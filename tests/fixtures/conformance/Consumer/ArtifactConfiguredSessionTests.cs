using System.Collections.Concurrent;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class ArtifactConfiguredSessionTests
{
    [Fact]
    public void Invalid_reference_observations_cannot_admit_negative_counts_or_missing_available_revisions()
    {
        Assert.Throws<ArgumentException>(() => new ArtifactReferenceObservation(true, -1, Guid.NewGuid()));
        Assert.Throws<ArgumentException>(() => new ArtifactReferenceObservation(true, 0, Guid.Empty));
        Assert.Throws<ArgumentException>(() => new ArtifactReferenceObservation(false, 1, Guid.Empty));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Actual_configured_limits_survive_compatible_or_logical_reopen(string provider)
    {
        await using var resources = new RecordingDirectories();
        var limits = new ArtifactLimits(artifactBytes: 1024, stagingBytes: 2048, transferSlots: 1, waitingCalls: 0);
        var original = await CreateAsync(provider, Context(resources), new(limits), default);
        var current = original;
        try
        {
            Assert.Equal(limits, current.Store.Capabilities.Limits);
            Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await current.Store.ReserveWriteAsync(new(new ArtifactExpectations(1025)), new(), default)).Code);
            await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
            current = await original.ReopenAsync(default);
            Assert.Equal(limits, current.Store.Capabilities.Limits);
            Assert.True(current.Ready);
            Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await current.Store.ReserveWriteAsync(new(new ArtifactExpectations(1025)), new(), default)).Code);
            await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
        }
        finally { await current.DisposeAsync(); }
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Timed_out_reference_query_stays_owned_through_reopen_or_final_settlement(string provider, bool reopen)
    {
        await using var resources = new RecordingDirectories();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var options = new ArtifactAssertionOptions(references: async (stamp, token) =>
        {
            entered.TrySetResult();
            await release.Task;
            return new ArtifactReferenceObservation(true, 0, Guid.NewGuid());
        });
        var original = await CreateAsync(provider, Context(resources), options, default);
        var current = original;
        Task<IArtifactAssertionSession>? reopening = null;
        Task? disposing = null;
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            var query = original.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Deletion,
                original.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)),
                new(TimeSpan.FromMilliseconds(20)), default).AsTask();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete,
                Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(await query).Code);
            if (reopen) { reopening = original.ReopenAsync(default).AsTask(); }
            else
            {
                disposing = original.DisposeAsync().AsTask();
                await resources.Observing.Task.WaitAsync(TimeSpan.FromSeconds(5));
                Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
            }
            Assert.False(original.Ready);
            Assert.False(reopening is { IsCompleted: true } || disposing is { IsCompleted: true });
        }
        finally
        {
            release.TrySetResult();
            if (reopening is not null)
            {
                current = await reopening.WaitAsync(TimeSpan.FromSeconds(5));
                Assert.True(current.Ready);
            }
            if (disposing is not null) { await disposing.WaitAsync(TimeSpan.FromSeconds(5)); }
            await current.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Current_reference_queries_fence_deletion_on_each_actual_generation(string provider)
    {
        await using var resources = new RecordingDirectories();
        var liveReferences = 1;
        var queries = 0;
        var queried = new ConcurrentQueue<ArtifactStamp>();
        var options = new ArtifactAssertionOptions(references: (stamp, token) =>
        {
            token.ThrowIfCancellationRequested();
            Interlocked.Increment(ref queries);
            queried.Enqueue(stamp);
            return ValueTask.FromResult(new ArtifactReferenceObservation(
                true, Volatile.Read(ref liveReferences), Guid.NewGuid()));
        });
        var original = await CreateAsync(provider, Context(resources), options, default);
        var current = original;
        try
        {
            for (var generation = 0; generation < 2; generation++)
            {
                Volatile.Write(ref liveReferences, 1);
                var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
                var denied = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                    await current.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default)).Value;
                Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await current.Store.DeleteAsync(denied, new(), default)).Code);
                Volatile.Write(ref liveReferences, 0);
                var allowed = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                    await current.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default)).Value;
                Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
                    await current.Store.DeleteAsync(allowed, new(), default));
                Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                    await current.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
                Assert.Contains(receipt.Stamp, queried);
                if (generation == 0) { current = await original.ReopenAsync(default); }
            }
            Assert.True(Volatile.Read(ref queries) >= 4);
        }
        finally { await current.DisposeAsync(); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Unavailable_reference_query_cannot_become_an_optimistic_zero_reference_decision(string provider)
    {
        await using var resources = new RecordingDirectories();
        var options = new ArtifactAssertionOptions(references: (stamp, token) =>
        {
            token.ThrowIfCancellationRequested();
            return ValueTask.FromResult(new ArtifactReferenceObservation(false, 0, Guid.Empty));
        });
        await using var session = await CreateAsync(provider, Context(resources), options, default);
        var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        var deletion = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
            await session.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default)).Value;
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await session.Store.DeleteAsync(deletion, new(), default)).Code);
        await using var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(
            await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Value;
    }

    private static ValueTask<IArtifactAssertionSession> CreateAsync(
        string provider, ConformanceRunContext context, ArtifactAssertionOptions options, CancellationToken cancellationToken) =>
        provider switch
        {
            "local" => LocalArtifactAssertionSessions.CreateAsync(context, options, cancellationToken),
            "object" => ObjectArtifactAssertionSessions.CreateAsync(context, options, cancellationToken),
            _ => throw new ArgumentException("BindingInvalid")
        };

    private static ConformanceRunContext Context(RecordingDirectories resources) => new(
        Guid.NewGuid(), "arbitrary-not-a-setup-selector", TimeProvider.System, resources, new ConformanceEvidenceBuffer());
}
