using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;

internal static class ArtifactNonCooperativeScenario
{
    public static async Task<int> ExecuteAsync(string[] args)
    {
        var safeEvents = Environment.GetEnvironmentVariable("HOARD_CONFORMANCE_SAFE_EVENTS") switch
        {
            null => false,
            "1" => true,
            _ => throw new ArgumentException("Unsupported artifact non-cooperative event mode.")
        };
        var root = Path.GetFullPath(args[1]);
        var provider = args[2];
        var scenario = args[3];
        var run = Guid.Parse(args[4]);
        if (provider is not ("local" or "object") || scenario is not ("source" or "destination" or "native"))
        { throw new ArgumentException("Unknown non-cooperative artifact scenario."); }
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var localFaults = new LocalFaultControls();
        var objectFaults = new ObjectFaultControls();
        IArtifactStoreLifetime lifetime = provider == "local"
            ? new LocalArtifactStore(root, controls: localFaults) : new ObjectArtifactStore(root, controls: objectFaults);
        Need(await lifetime.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority,
            new ArtifactLimits(transferSlots: 1, waitingCalls: 0)), new(), default));
        var store = (IArtifactStore)lifetime;
        var stall = new Stall();
        var source = new StalledSource(stall);
        var destination = new StalledDestination(stall);
        ArtifactStamp? stamp = null;
        ArtifactCleanupState cleanup;
        ArtifactFailureCode callerCode;
        using var cancellation = new CancellationTokenSource();
        if (scenario == "source")
        {
            var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            var stage = store.StageAsync(ticket, source, new(), cancellation.Token).AsTask();
            await stall.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            cancellation.Cancel();
            var failed = Retained(await stage.WaitAsync(TimeSpan.FromSeconds(2)));
            Require(failed.Code == ArtifactFailureCode.CancelledBeforeCommit);
            cleanup = failed.Cleanup;
            callerCode = failed.Code;
        }
        else
        {
            var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var bytes = new MemoryStream("owned-child-control"u8.ToArray());
            var staged = Need(await store.StageAsync(ticket, bytes, new(), default));
            stamp = Need(await store.CommitAsync(staged, new(), default)).Stamp;
            if (scenario == "destination")
            {
                var read = Need(await store.OpenReadAsync(new(stamp.Identity.Digest), new(), default));
                var copy = read.CopyToAsync(destination, new(), cancellation.Token).AsTask();
                await stall.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
                cancellation.Cancel();
                var failed = Retained(await copy.WaitAsync(TimeSpan.FromSeconds(2)));
                Require(failed.Code == ArtifactFailureCode.CancelledBeforeCommit);
                cleanup = failed.Cleanup;
                callerCode = failed.Code;
                Require(Retained(await read.CloseAsync(new(TimeSpan.FromMilliseconds(50)), default)).Code
                    == ArtifactFailureCode.CleanupIncomplete);
            }
            else
            {
                var deletion = Need(await store.ReserveDeleteAsync(new(stamp), new(), default));
                if (provider == "local") { localFaults.BeforeRecordWrite = stall.BlockNative; }
                else { objectFaults.BeforeObjectDelete = stall.BlockNative; }
                var delete = store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(100)), default).AsTask();
                await stall.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
                var failed = Retained(await delete.WaitAsync(TimeSpan.FromSeconds(2)));
                Require(failed.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
                cleanup = failed.Cleanup;
                callerCode = failed.Code;
            }
        }
        await InspectAsync("contained");
        using var parent = new CancellationTokenSource(TimeSpan.FromMinutes(4));
        Require(await Console.In.ReadLineAsync(parent.Token) == "inspect");
        await InspectAsync("inspected");
        // Only the owning parent terminates this deliberately uncooperative child.
        await Task.Delay(Timeout.InfiniteTimeSpan, parent.Token);
        return 1;

        async Task InspectAsync(string phase)
        {
            var idle = lifetime switch
            {
                LocalArtifactStore local => local.WhenIdleForQualificationAsync(),
                ObjectArtifactStore objects => objects.WhenIdleForQualificationAsync(),
                _ => throw new InvalidOperationException("Unknown artifact child store.")
            };
            Require(!idle.IsCompleted && stall.Count == 1 && !source.WasDisposed && !destination.WasDisposed);
            var admission = Retained(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
            Require(admission.Code == ArtifactFailureCode.CleanupIncomplete);
            var protectionRetained = false;
            if (stamp is not null)
            {
                var operation = scenario == "destination" ? ArtifactProtectionOperation.Deletion : ArtifactProtectionOperation.Read;
                var request = new ArtifactProtectionRequest(Guid.NewGuid(), operation, identity, stamp.Identity.Digest,
                    new ArtifactOption<ArtifactStamp>.Some(stamp));
                var blocked = await authority.AcquireAsync(request, new(TimeSpan.FromMilliseconds(50)), default);
                if (blocked is ArtifactResult<IArtifactProtectionGuard>.Success unexpected)
                {
                    await unexpected.Value.DisposeAsync();
                    throw new InvalidOperationException("Non-cooperative artifact work lost protection.");
                }
                Require(blocked is ArtifactResult<IArtifactProtectionGuard>.Failure
                { Code: ArtifactFailureCode.DeadlineExceeded });
                protectionRetained = true;
            }
            var shutdown = Retained(await lifetime.StopAsync(new(TimeSpan.FromMilliseconds(50)), default)
                .AsTask().WaitAsync(TimeSpan.FromSeconds(2)));
            Require(shutdown.Code == ArtifactFailureCode.CleanupIncomplete && !idle.IsCompleted);
            IArtifactStoreLifetime competing = provider == "local" ? new LocalArtifactStore(root) : new ObjectArtifactStore(root);
            var duplicate = await competing.InitializeAsync(new(provider == "local" ? ArtifactInitializationMode.ReopenCompatible
                : ArtifactInitializationMode.CreateEmpty, identity, authority), new(), default);
            Require(duplicate is ArtifactResult<ArtifactAdmission>.Failure { Code: ArtifactFailureCode.Unavailable });
            Need(await competing.StopAsync(new(), default));
            var ready = lifetime switch
            {
                LocalArtifactStore local => local.Ready,
                ObjectArtifactStore objects => objects.Ready,
                _ => throw new InvalidOperationException("Unknown artifact child store.")
            };
            Require(!ready && !idle.IsCompleted && stall.Count == 1);
            var observation = JsonSerializer.Serialize(new
            {
                eventName = "noncooperative",
                phase,
                pid = Environment.ProcessId,
                runId = run,
                provider,
                scenario,
                durableCrashProof = false,
                cleanup = cleanup.ToString(),
                callerCode = callerCode.ToString(),
                admissionCode = admission.Code.ToString(),
                shutdownCode = shutdown.Code.ToString(),
                enteredWorkers = stall.Count,
                workerPending = !idle.IsCompleted,
                borrowedStreamsIntact = !source.WasDisposed && !destination.WasDisposed,
                rootStillOwned = true,
                readinessBlocked = !ready,
                protectionRetained
            });
            if (safeEvents)
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(observation);
                if (bytes.Length > 8192)
                { throw new InvalidOperationException("Artifact non-cooperative proof exceeded its bound."); }
                using (var output = new FileStream(Path.Combine(root, $"noncooperative-{phase}.json"),
                    FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    output.Write(bytes);
                    output.Flush(flushToDisk: true);
                }
                var offset = scenario switch { "source" => 0, "destination" => 1, "native" => 2, _ => throw new InvalidOperationException() };
                var value = (phase == "contained" ? 60 : 70) + offset;
                Console.WriteLine(JsonSerializer.Serialize(new { @event = "barrier", code = "None", value }));
            }
            else
            { Console.WriteLine(observation); }
            await Console.Out.FlushAsync();
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
        private readonly ManualResetEventSlim native = new();
        public int Count => Volatile.Read(ref count);
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<int> Read { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Write { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public void Enter() { Interlocked.Increment(ref count); Entered.TrySetResult(); }
        public void BlockNative() { Enter(); native.Wait(); }
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
