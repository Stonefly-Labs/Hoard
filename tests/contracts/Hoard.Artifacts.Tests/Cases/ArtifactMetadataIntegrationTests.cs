using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactMetadataIntegrationTests
{
    [Theory]
    [InlineData("local", "sqlite")]
    [InlineData("local", "memory")]
    [InlineData("object", "sqlite")]
    [InlineData("object", "memory")]
    public async Task New_reference_cannot_cross_an_admitted_zero_reference_deletion(string provider, string metadataProvider)
    {
        using var root = PrivateRoot();
        await using var session = await ArtifactMetadataFixtureSession.CreateForQualificationAsync(provider, metadataProvider, root.Path);
        await Assertions(session).ReferenceDuringDeletionAsync(() => session.Artifacts.Authority.WaitingAdmissions, default);
    }

    [Theory]
    [InlineData("local", "sqlite")]
    [InlineData("local", "memory")]
    [InlineData("object", "sqlite")]
    [InlineData("object", "memory")]
    public async Task Failed_metadata_transaction_leaves_identifiable_committed_bytes_not_a_fabricated_entry(
        string provider, string metadataProvider)
    {
        using var root = PrivateRoot();
        await using var session = await ArtifactMetadataFixtureSession.CreateForQualificationAsync(provider, metadataProvider, root.Path);
        await Assertions(session).FailedTransactionAsync(default);
    }

    [Theory]
    [InlineData("local", "sqlite")]
    [InlineData("local", "memory")]
    [InlineData("object", "sqlite")]
    [InlineData("object", "memory")]
    public async Task Actual_metadata_references_deny_removal_until_the_reference_transaction_commits(
        string provider, string metadataProvider)
    {
        using var root = PrivateRoot();
        await using var session = await ArtifactMetadataFixtureSession.CreateForQualificationAsync(provider, metadataProvider, root.Path);
        await Assertions(session).ActualReferencesAsync(default);
    }

    [Theory]
    [InlineData("local", "sqlite")]
    [InlineData("local", "memory")]
    [InlineData("object", "sqlite")]
    [InlineData("object", "memory")]
    public async Task Lost_metadata_acknowledgment_keeps_real_reference_protection_until_physical_settlement(
        string provider, string metadataProvider)
    {
        using var root = PrivateRoot();
        await using var session = await ArtifactMetadataFixtureSession.CreateForQualificationAsync(provider, metadataProvider, root.Path);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await Assertions(session).LostAcknowledgmentProtectionAsync(
            () => session.Controls.SetObserver("M1", () => { entered.TrySetResult(); return new(release.Task); }),
            () => entered.Task, () => release.TrySetResult(),
            session.Artifacts.WhenIdleForQualificationAsync, session.WhenMetadataIdleAsync, default);
    }

    private static ArtifactMetadataIntegrationAssertions Assertions(ArtifactMetadataFixtureSession session) =>
        new(session.Artifacts.Store, session.Metadata, session.Artifacts.Identity, session.Artifacts.Authority,
            session.Publication.Encode);

    internal static ArtifactTestRoot PrivateRoot()
    {
        if (OperatingSystem.IsWindows()) { throw new InvalidOperationException("Artifact qualification requires a Unix host."); }
        var root = new ArtifactTestRoot();
        Directory.CreateDirectory(root.Path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        return root;
    }
}
