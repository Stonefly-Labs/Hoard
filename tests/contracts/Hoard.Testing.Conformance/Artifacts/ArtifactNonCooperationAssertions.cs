using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed record ArtifactNonCooperationReadback(
    ArtifactCleanupState Cleanup, ArtifactFailureCode CallerCode, ArtifactFailureCode AdmissionCode,
    ArtifactFailureCode ShutdownCode, long EnteredWorkers, bool WorkerPending, bool BorrowedStreamsIntact,
    bool RootStillOwned, bool ReadinessBlocked, bool ProtectionRetained);

public static class ArtifactNonCooperationAssertions
{
    public static async Task ExecuteAsync(
        IArtifactStore store, IArtifactStoreLifetime lifetime, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, string scenario,
        Func<CancellationToken, ValueTask<IArtifactSynchronousHold>> holdNative,
        Func<Task> whenIdle, Func<ArtifactInitializationObservation> initialization,
        Func<ArtifactInitializationMode, CancellationToken, ValueTask<ArtifactCompetingInitializationObservation>> probeCompeting,
        Func<string, ArtifactNonCooperationReadback, ValueTask> publish, CancellationToken cancellationToken)
    {
        if (scenario is not ("source" or "destination" or "native"))
        { throw new ArgumentException("EvidenceSchemaInvalid"); }
        var stall = new Stall();
        var source = new StalledSource(stall);
        var destination = new StalledDestination(stall);
        IArtifactSynchronousHold? native = null;
        ArtifactStamp? stamp = null;
        ArtifactCleanupState cleanup;
        ArtifactFailureCode callerCode;
        using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        if (scenario == "source")
        {
            var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            var stage = store.StageAsync(ticket, source, new(), cancellation.Token).AsTask();
            await stall.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10), cancellationToken);
            cancellation.Cancel();
            var failed = Retained(await stage.WaitAsync(TimeSpan.FromSeconds(2), cancellationToken));
            Require(failed.Code == ArtifactFailureCode.CancelledBeforeCommit);
            cleanup = failed.Cleanup;
            callerCode = failed.Code;
        }
        else
        {
            var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var bytes = new MemoryStream("owned-child-control"u8.ToArray());
            var staged = Need(await store.StageAsync(ticket, bytes, new(), cancellationToken));
            stamp = Need(await store.CommitAsync(staged, new(), cancellationToken)).Stamp;
            if (scenario == "destination")
            {
                var read = Need(await store.OpenReadAsync(new(stamp.Identity.Digest), new(), cancellationToken));
                var copy = read.CopyToAsync(destination, new(), cancellation.Token).AsTask();
                await stall.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10), cancellationToken);
                cancellation.Cancel();
                var failed = Retained(await copy.WaitAsync(TimeSpan.FromSeconds(2), cancellationToken));
                Require(failed.Code == ArtifactFailureCode.CancelledBeforeCommit);
                cleanup = failed.Cleanup;
                callerCode = failed.Code;
                Require(Retained(await read.CloseAsync(new(TimeSpan.FromMilliseconds(50)), cancellationToken)).Code
                    == ArtifactFailureCode.CleanupIncomplete);
            }
            else
            {
                var deletion = Need(await store.ReserveDeleteAsync(new(stamp), new(), cancellationToken));
                native = await holdNative(cancellationToken);
                var delete = store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(100)), cancellationToken).AsTask();
                await native.WaitForEntryAsync(cancellationToken);
                var failed = Retained(await delete.WaitAsync(TimeSpan.FromSeconds(2), cancellationToken));
                Require(failed.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
                cleanup = failed.Cleanup;
                callerCode = failed.Code;
            }
        }
        await InspectAsync("contained");
        await InspectAsync("inspected");
        // Only the owning parent terminates this deliberately uncooperative child.
        await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);

        async Task InspectAsync(string phase)
        {
            var idle = whenIdle();
            var count = native?.ObservationCount ?? stall.Count;
            Require(!idle.IsCompleted && count == 1 && !source.WasDisposed && !destination.WasDisposed);
            var admission = Retained(await store.ReserveWriteAsync(
                new(new ArtifactExpectations(1)), new(), cancellationToken));
            Require(admission.Code == ArtifactFailureCode.CleanupIncomplete);
            var protectionRetained = false;
            if (stamp is not null)
            {
                var operation = scenario == "destination" ? ArtifactProtectionOperation.Deletion : ArtifactProtectionOperation.Read;
                var request = new ArtifactProtectionRequest(Guid.NewGuid(), operation, identity, stamp.Identity.Digest,
                    new ArtifactOption<ArtifactStamp>.Some(stamp));
                var blocked = await authority.AcquireAsync(request, new(TimeSpan.FromMilliseconds(50)), cancellationToken);
                if (blocked is ArtifactResult<IArtifactProtectionGuard>.Success unexpected)
                {
                    await unexpected.Value.DisposeAsync();
                    throw new InvalidOperationException("Non-cooperative artifact work lost protection.");
                }
                Require(blocked is ArtifactResult<IArtifactProtectionGuard>.Failure
                { Code: ArtifactFailureCode.DeadlineExceeded });
                protectionRetained = true;
            }
            var shutdown = Retained(await lifetime.StopAsync(new(TimeSpan.FromMilliseconds(50)), cancellationToken)
                .AsTask().WaitAsync(TimeSpan.FromSeconds(2), cancellationToken));
            Require(shutdown.Code == ArtifactFailureCode.CleanupIncomplete && !idle.IsCompleted);
            var mode = store.Capabilities.Durability == ArtifactDurability.LocalProcessCrash
                ? ArtifactInitializationMode.ReopenCompatible : ArtifactInitializationMode.CreateEmpty;
            var competing = await probeCompeting(mode, cancellationToken);
            Require(competing.Admission is ArtifactResult<ArtifactAdmission>.Failure { Code: ArtifactFailureCode.Unavailable });
            Need(competing.Shutdown);
            var observed = initialization();
            count = native?.ObservationCount ?? stall.Count;
            Require(observed.RootExists && !observed.Ready && !idle.IsCompleted && count == 1);
            await publish(phase, new(cleanup, callerCode, admission.Code, shutdown.Code, count,
                !idle.IsCompleted, !source.WasDisposed && !destination.WasDisposed,
                observed.RootExists, !observed.Ready, protectionRetained));
        }
    }

    private static T Need<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException("Artifact child control operation failed.");

    private static ArtifactResult<T>.Failure Retained<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Failure { Cleanup: ArtifactCleanupState.RetainedLiveOwnership } failure
            ? failure : throw new InvalidOperationException("Artifact child lost live ownership.");

    private static void Require(bool condition)
    {
        if (!condition) { throw new InvalidOperationException("Artifact non-cooperative containment assertion failed."); }
    }

    private sealed class Stall
    {
        private int count;
        public int Count => Volatile.Read(ref count);
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<int> Read { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Write { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public void Enter() { Interlocked.Increment(ref count); Entered.TrySetResult(); }
    }

    private sealed class StalledSource(Stall stall) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        { stall.Enter(); return new(stall.Read.Task); }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }

    private sealed class StalledDestination(Stall stall) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
        { stall.Enter(); return new(stall.Write.Task); }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
