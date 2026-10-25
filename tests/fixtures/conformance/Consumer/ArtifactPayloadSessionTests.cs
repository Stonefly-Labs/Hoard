using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class ArtifactPayloadSessionTests
{
    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Scoped_unclaimed_cleanup_failure_retains_actual_work_until_repaired_settlement(
        string provider, bool readSession)
    {
        await using var resources = new RecordingDirectories();
        var session = await CreateAsync(provider, resources);
        try { await ArtifactFailureAssertions.ScopedUnclaimedCleanupAsync(session, readSession, default); }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Scoped_capacity_failure_is_real_recoverable_and_does_not_poison_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories();
        var session = await CreateAsync(provider, resources, new(
            limits: new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0)));
        try { await ArtifactFailureAssertions.ScopedCapacityAsync(session, default); }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Ordinary_capacity_shaped_observer_error_still_faults_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var session = await CreateAsync(provider, resources);
        var failure = new IOException("ordinary-observer-capacity-error", 28);
        try
        {
            await using var observation = await session.ObserveBoundaryAsync(ArtifactObservationPoint.StagePrefix,
                () => ValueTask.FromException(failure), default);
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("ordinary observer failure"u8.ToArray());
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await session.Store.StageAsync(ticket, source, new(), default)).Code);
            await session.AwaitSettlementAsync(default);
            Assert.False(session.Ready);
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var actual = Assert.Single(resources.Settlements).Value;
        Assert.True(actual.IsFaulted);
        Assert.Contains(failure, actual.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Direct_verification_observation_holds_new_and_duplicate_publication_before_acknowledgement(
        string provider, bool duplicate)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources);
        await ArtifactObservationAssertions.DirectVerificationAsync(session, duplicate, default);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Actual_payload_damage_invalidates_copy_and_later_open(string provider, bool truncate)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources);
        var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        await session.DamagePayloadAsync(receipt.Stamp, truncate, default);
        await using (var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(
            await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Value)
        {
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await read.CopyToAsync(destination, new(), default)).Code);
            Assert.True(destination.CanWrite);
        }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Held_native_payload_handle_stays_owned_through_reopen_or_final_settlement(string provider, bool reopen)
    {
        await using var resources = new RecordingDirectories();
        var original = await CreateAsync(provider, resources);
        var current = original;
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task? damaging = null;
        Task<IArtifactAssertionSession>? reopening = null;
        Task? disposing = null;
        using var cancellation = new CancellationTokenSource();
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            await using var observation = await original.ObserveBoundaryAsync(ArtifactObservationPoint.PayloadDamage, async () =>
            {
                entered.TrySetResult();
                await release.Task;
            }, default);
            damaging = original.DamagePayloadAsync(receipt.Stamp, false, cancellation.Token).AsTask();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            cancellation.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => damaging);
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
            if (damaging is not null) { await Assert.ThrowsAnyAsync<OperationCanceledException>(() => damaging); }
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
    public async Task Foreign_incarnation_cannot_damage_current_payload(string provider)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources);
        var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        var foreign = new ArtifactStamp(receipt.Stamp.Store, receipt.Stamp.Identity, Guid.NewGuid());
        await Assert.ThrowsAsync<InvalidOperationException>(() => session.DamagePayloadAsync(foreign, false, default).AsTask());
        await using var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(
            await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Value;
        using var destination = new MemoryStream();
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Success>(
            await read.CopyToAsync(destination, new(), default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Failed_damage_observer_preserves_bytes_and_faults_final_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var session = await CreateAsync(provider, resources);
        var failure = new InvalidOperationException("controlled-payload-observer-failure");
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
            var original = await ArtifactPublicationAssertions.ReadAsync(session.Store, receipt.Stamp, default);
            await using var observation = await session.ObserveBoundaryAsync(ArtifactObservationPoint.PayloadDamage,
                () => ValueTask.FromException(failure), default);
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                session.DamagePayloadAsync(receipt.Stamp, false, default).AsTask());
            await session.AwaitSettlementAsync(default);
            Assert.Equal(original, await ArtifactPublicationAssertions.ReadAsync(session.Store, receipt.Stamp, default));
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var actual = Assert.Single(resources.Settlements).Value;
        Assert.True(actual.IsFaulted);
        Assert.Contains(failure, actual.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Removed_incarnation_cannot_damage_same_digest_replacement(string provider)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources, new(references: (stamp, token) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        var old = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        var original = await ArtifactPublicationAssertions.ReadAsync(session.Store, old.Stamp, default);
        var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
            await session.Store.ReserveDeleteAsync(new(old.Stamp), new(), default)).Value;
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
            await session.Store.DeleteAsync(ticket, new(), default));
        var replacement = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        Assert.Equal(old.Stamp.Identity.Digest, replacement.Stamp.Identity.Digest);
        Assert.NotEqual(old.Stamp.Incarnation, replacement.Stamp.Incarnation);
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            session.DamagePayloadAsync(old.Stamp, false, default).AsTask());
        Assert.Equal(original, await ArtifactPublicationAssertions.ReadAsync(session.Store, replacement.Stamp, default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Stale_session_cannot_damage_reopened_payload(string provider)
    {
        await using var resources = new RecordingDirectories();
        await using var original = await CreateAsync(provider, resources);
        var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
        await using var current = await original.ReopenAsync(default);
        var replacement = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
        var bytes = await ArtifactPublicationAssertions.ReadAsync(current.Store, replacement.Stamp, default);
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            original.DamagePayloadAsync(receipt.Stamp, false, default).AsTask());
        Assert.Equal(bytes, await ArtifactPublicationAssertions.ReadAsync(current.Store, replacement.Stamp, default));
    }

    [Fact]
    public async Task Object_old_epoch_cannot_damage_current_incarnation()
    {
        await using var resources = new RecordingDirectories();
        await using var original = await CreateAsync("object", resources);
        var old = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
        await using var current = await original.ReopenAsync(default);
        var replacement = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
        var bytes = await ArtifactPublicationAssertions.ReadAsync(current.Store, replacement.Stamp, default);
        var foreignEpoch = new ArtifactStamp(old.Stamp.Store, replacement.Stamp.Identity, replacement.Stamp.Incarnation);
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            current.DamagePayloadAsync(foreignEpoch, false, default).AsTask());
        Assert.Equal(bytes, await ArtifactPublicationAssertions.ReadAsync(current.Store, replacement.Stamp, default));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Empty_payload_damage_is_explicit_and_never_false_success(string provider, bool truncate)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources);
        using var source = new ArtifactPublicationAssertions.ShortSource([]);
        var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1), default);
        if (truncate)
        {
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                session.DamagePayloadAsync(receipt.Stamp, true, default).AsTask());
            Assert.Empty(await ArtifactPublicationAssertions.ReadAsync(session.Store, receipt.Stamp, default));
        }
        else
        {
            await session.DamagePayloadAsync(receipt.Stamp, false, default);
            await using var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(
                await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Value;
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await read.CopyToAsync(Stream.Null, new(), default)).Code);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Incompatible_open_read_handle_rejects_damage_without_changing_bytes(string provider)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await CreateAsync(provider, resources);
        var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, default);
        var original = await ArtifactPublicationAssertions.ReadAsync(session.Store, receipt.Stamp, default);
        await using (var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(
            await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Value)
        {
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                session.DamagePayloadAsync(receipt.Stamp, false, default).AsTask());
            using var destination = new MemoryStream();
            Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Success>(
                await read.CopyToAsync(destination, new(), default));
            Assert.Equal(original, destination.ToArray());
        }
        await session.AwaitSettlementAsync(default);
        Assert.True(session.Ready);
    }

    private static ValueTask<IArtifactAssertionSession> CreateAsync(
        string provider, RecordingDirectories resources, ArtifactAssertionOptions? options = null)
    {
        var context = new ConformanceRunContext(Guid.NewGuid(), "not-a-damage-selector",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        return provider switch
        {
            "local" => LocalArtifactAssertionSessions.CreateAsync(context, options ?? new(), default),
            "object" => ObjectArtifactAssertionSessions.CreateAsync(context, options ?? new(), default),
            _ => throw new ArgumentException("BindingInvalid")
        };
    }
}
