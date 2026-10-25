using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Conformance.Tests;

public sealed class AuthorityIntegrationTests
{
    public static IEnumerable<object[]> Rows()
    {
        foreach (var provider in new[] { "local", "object" })
        {
            foreach (var metadata in new[] { "memory", "sqlite" })
            {
                foreach (var consumer in new[] {
                    "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
                    "incarnation", "reader", "foreign-authority", "shutdown" })
                { yield return [provider, metadata, consumer]; }
            }
        }
    }

    [Theory]
    [MemberData(nameof(Rows))]
    public async Task Actual_compositions_preserve_shared_authority(
        string provider, string metadataProvider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var root = await resources.AllocateDirectoryAsync(default);
        var session = await ArtifactMetadataFixtureSession.CreateForQualificationAsync(
            provider, metadataProvider, root.DirectoryPath);
        try
        {
            var assertions = new ArtifactMetadataIntegrationAssertions(
                session.Artifacts.Store, session.Metadata, session.Artifacts.Identity,
                session.Artifacts.Authority, session.Publication.Encode);
            await (consumer switch
            {
                "reference-admission" => assertions.ReferenceDuringDeletionAsync(
                    () => session.Artifacts.Authority.WaitingAdmissions, default),
                "failed-transaction" => assertions.FailedTransactionAsync(default),
                "live-references" => assertions.ActualReferencesAsync(default),
                "lost-acknowledgment" => LostAcknowledgmentAsync(session, assertions),
                "incarnation" => ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
                    session.Artifacts.Store, session.Artifacts.Maintenance, session.Artifacts.Identity, default),
                "reader" => ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(session.Artifacts.Store, default),
                "foreign-authority" => new ArtifactAuthorityAssertions(session.Artifacts.Identity).RejectCopiedHandlesAsync(
                    session.Artifacts.Authority, new ArtifactCoordinationAuthority(session.Artifacts.Identity), default),
                "shutdown" => ShutdownAsync(session, root.DirectoryPath),
                _ => throw new ArgumentException("BindingInvalid")
            });
        }
        finally
        {
            var settlement = session.CloseAdmissionsAndObserveSettlementForQualificationAsync();
            var cleanup = await resources.ReleaseAsync(root, settlement, default);
            Assert.Equal(ConformanceOwnershipState.Settling, cleanup.State);
            await settlement;
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    private static async Task LostAcknowledgmentAsync(
        ArtifactMetadataFixtureSession session, ArtifactMetadataIntegrationAssertions assertions)
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await assertions.LostAcknowledgmentProtectionAsync(
            () => session.Controls.SetObserver("M1", () => { entered.TrySetResult(); return new(release.Task); }),
            () => entered.Task, () => release.TrySetResult(),
            session.Artifacts.WhenIdleForQualificationAsync, session.WhenMetadataIdleAsync, default);
    }

    private static async Task ShutdownAsync(ArtifactMetadataFixtureSession session, string root)
    {
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            session.Artifacts.Identity, new ArtifactDigest(new string('a', 64)));
        await using var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await session.Artifacts.Authority.AcquireAsync(request, new(), default)).Value;
        var settlement = session.CloseAdmissionsAndObserveSettlementForQualificationAsync();
        Assert.Same(settlement, session.CloseAdmissionsAndObserveSettlementForQualificationAsync());
        Assert.False(settlement.IsCompleted);
        Assert.True(Directory.Exists(root));
        var next = new ArtifactProtectionRequest(Guid.NewGuid(), request.Operation, request.Store, request.Digest);
        var rejected = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await session.Artifacts.Authority.AcquireAsync(next, new(), default));
        Assert.Equal(ArtifactFailureCode.Unavailable, rejected.Code);
        await guard.DisposeAsync();
        await settlement.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.True(Directory.Exists(root));
    }
}
