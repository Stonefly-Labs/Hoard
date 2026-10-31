using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class MemoryBindingOwnershipTests
{
    [Fact]
    public async Task Actual_allocator_retains_pending_memory_work_and_retry_preserves_the_failed_observation()
    {
        var repository = FindRepository();
        var parent = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Hoard", "conformance-owned-tests");
        Directory.CreateDirectory(parent);
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
        var root = Path.Combine(parent, "memory-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        using var allocator = ConformanceResourceAllocator.Open(root, repository, TimeSpan.FromMilliseconds(20));
        var context = new ConformanceRunContext(Guid.NewGuid(), "actual-memory-ownership",
            new MetadataConformanceClock(new(1_800_000_000_000)), allocator, new ConformanceEvidenceBuffer());
        var session = await new MemoryBinding(new string('a', 64)).CreateSessionAsync(context, default);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task? disposing = null;
        Task<MetadataResult<MetadataCommitReceipt>>? committing = null;
        await using var observation = await session.Faults.ObserveBoundaryAsync(
            MetadataObservationPoint.BeforeCommitDecision,
            () => { entered.TrySetResult(); return new(release.Task); }, default);
        try
        {
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
                await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            var ticket = Assert.IsType<MetadataResult<MetadataOperationTicket>.Success>(
                await session.Store.ReserveOperationAsync(new(), default)).Value;
            var registry = new MetadataRegistry
            {
                Id = new(Guid.NewGuid()),
                Ecosystem = new("nuget"),
                Upstream = new("https://example.invalid/v3/"),
                Enabled = true,
                Label = new("synthetic"),
                PolicyId = new MetadataOption<MetadataId>.None(),
                Secret = new MetadataOption<MetadataSecretReference>.None(),
                Revision = new(Guid.NewGuid())
            };
            committing = session.Store.CommitAsync(new(ticket,
                [new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent())],
                new MetadataOption<MetadataLeaseGuard>.None()), new(TimeSpan.FromMilliseconds(200)), default).AsTask();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(MetadataFailureCode.DeadlineExceeded,
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await committing).Code);
            disposing = session.DisposeAsync().AsTask();
            await WaitForRetained(session);
            Assert.False(disposing.IsCompleted);
            Assert.Throws<InvalidOperationException>(() => allocator.Dispose());
            Assert.Equal(ConformanceDiagnosticCode.CleanupIncomplete, allocator.ObserveLedger()[^1].Observation.Reason);
            release.TrySetResult();
            await Assert.ThrowsAsync<InvalidOperationException>(() => disposing);
            await session.DisposeAsync();
            var cleanup = await session.ObserveCleanupAsync(default);
            Assert.Equal(ConformanceOwnershipState.Settling, cleanup.State);
            Assert.Single(cleanup.ResourceIds);
            Assert.Contains(allocator.ObserveLedger(), item => item.Observation.State == ConformanceOwnershipState.Retained);
            Assert.DoesNotContain(allocator.ObserveLedger(), item => item.Observation.State == ConformanceOwnershipState.Released);
            Assert.Single(Directory.GetDirectories(root));
        }
        finally
        {
            release.TrySetResult();
            try { if (disposing is not null) { await Record.ExceptionAsync(() => disposing); } }
            finally
            {
                if (committing is not null) { await committing.WaitAsync(TimeSpan.FromSeconds(10)); }
                await session.Faults.AwaitSettlementAsync(default);
                await session.DisposeAsync();
                allocator.Dispose();
                foreach (var directory in Directory.GetDirectories(root)) { Directory.Delete(directory); }
                Directory.Delete(root);
            }
        }
    }

    private static async Task WaitForRetained(IMetadataConformanceSession session)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        while ((await session.ObserveCleanupAsync(timeout.Token)).State != ConformanceOwnershipState.Retained)
        { await Task.Delay(1, timeout.Token); }
    }

    private static string FindRepository()
    {
        for (var current = new DirectoryInfo(AppContext.BaseDirectory); current is not null; current = current.Parent)
        {
            if (File.Exists(Path.Combine(current.FullName, "Hoard.slnx"))) { return current.FullName; }
        }
        throw new InvalidOperationException("PrerequisiteMissing");
    }
}
