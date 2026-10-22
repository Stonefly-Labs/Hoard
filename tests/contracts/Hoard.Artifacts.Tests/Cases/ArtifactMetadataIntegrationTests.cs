using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

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
        var receipt = await PublishAsync(session.Artifacts.Store);
        var (registry, package) = SeedRecords();
        await CommitAsync(session.Metadata, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var operation = Guid.NewGuid();
        var request = new ArtifactProtectionRequest(operation, ArtifactProtectionOperation.Deletion,
            session.Artifacts.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        var exclusive = Success(await session.Artifacts.Authority.AcquireAsync(request, new(), default));
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await session.Metadata.ReserveOperationAsync(new(), default));
        var publishing = session.Metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(session, receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default).AsTask();
        try
        {
            await WaitForReferenceAdmissionAsync(session.Artifacts.Authority, publishing);
            Assert.False(publishing.IsCompleted);
            await using var retained = Success(await session.Artifacts.Authority.RetainAsync(exclusive, request, new(), default));
            await exclusive.DisposeAsync();
            Assert.False(publishing.IsCompleted);
        }
        finally { await exclusive.DisposeAsync(); }
        MetadataSuccess(await publishing);
        var deletion = Success(await session.Artifacts.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await session.Artifacts.Store.DeleteAsync(deletion, new(), default)).Code);
        await AssertContentAsync(session.Artifacts.Store, receipt.Stamp);
    }

    private static async Task WaitForReferenceAdmissionAsync(ArtifactCoordinationAuthority authority, Task publication)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        while (authority.WaitingAdmissions == 0 && !publication.IsCompleted)
        {
            deadline.Token.ThrowIfCancellationRequested();
            await Task.Yield();
        }
        Assert.Equal(1, authority.WaitingAdmissions);
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
        var receipt = await PublishAsync(session.Artifacts.Store);
        var (_, package) = SeedRecords();
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await session.Metadata.ReserveOperationAsync(new(), default));
        var failed = await session.Metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(session, receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default);
        Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(failed);
        Assert.IsType<MetadataReadItem.NotFound>(MetadataSuccess(await session.Metadata.ReadAsync(new([entry.Selector]), new(), default)).Items[0]);
        var reconciled = Assert.IsType<ArtifactResolution.Committed>(Success(
            await session.Artifacts.Store.ReconcileAsync(receipt.Ticket, new(), default)));
        Assert.Equal(receipt, reconciled.Receipt);
        await AssertContentAsync(session.Artifacts.Store, receipt.Stamp);
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
        var receipt = await PublishAsync(session.Artifacts.Store);
        var (registry, package) = SeedRecords();
        await CommitAsync(session.Metadata, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var entry = Entry(package, receipt.Stamp);
        await CommitAsync(session.Metadata, new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(session, receipt)));
        var deletion = Success(await session.Artifacts.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await session.Artifacts.Store.DeleteAsync(deletion, new(), default)).Code);
        await AssertContentAsync(session.Artifacts.Store, receipt.Stamp);
        var current = Assert.IsType<MetadataCacheEntry>(Assert.IsType<MetadataReadItem.Found>(
            MetadataSuccess(await session.Metadata.ReadAsync(new([entry.Selector]), new(), default)).Items[0]).Record);
        await CommitAsync(session.Metadata, new MetadataMutation.DeleteCacheEntry(current.Identity, current.Revision));
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await session.Artifacts.Store.DeleteAsync(deletion, new(), default)).Outcome);
        var staleTicket = MetadataSuccess(await session.Metadata.ReserveOperationAsync(new(), default));
        Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await session.Metadata.CommitAsync(new(staleTicket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(session, receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default));
        Assert.IsType<MetadataReadItem.NotFound>(MetadataSuccess(await session.Metadata.ReadAsync(new([entry.Selector]), new(), default)).Items[0]);
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
        var receipt = await PublishAsync(session.Artifacts.Store);
        var (registry, package) = SeedRecords();
        await CommitAsync(session.Metadata, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await session.Metadata.ReserveOperationAsync(new(), default));
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        session.Controls.SetObserver("M1", () => { entered.TrySetResult(); return new(release.Task); });
        var committing = session.Metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(session, receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(TimeSpan.FromMilliseconds(150)), default).AsTask();
        var deletion = Success(await session.Artifacts.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            var failed = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
                await committing.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(MetadataFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await session.Artifacts.Store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(30)), default)).Code);
            await session.Artifacts.WhenIdleForQualificationAsync().WaitAsync(TimeSpan.FromSeconds(2));
            await AssertContentAsync(session.Artifacts.Store, receipt.Stamp);
        }
        finally
        {
            release.TrySetResult();
            await committing;
            await session.WhenMetadataIdleAsync();
        }
        Assert.IsType<MetadataResolution.Committed>(MetadataSuccess(await session.Metadata.ReconcileAsync(ticket, new(), default)));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await session.Artifacts.Store.DeleteAsync(deletion, new(), default)).Code);
    }

    private static readonly byte[] Content = "actual artifact metadata composition"u8.ToArray();
    private static ArtifactTestRoot PrivateRoot()
    {
        if (OperatingSystem.IsWindows()) { throw new InvalidOperationException("Artifact qualification requires a Unix host."); }
        var root = new ArtifactTestRoot();
        Directory.CreateDirectory(root.Path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        return root;
    }
    private static async Task<ArtifactMutationReceipt> PublishAsync(IArtifactStore store)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource(Content);
        var staged = Success(await store.StageAsync(ticket, source, new(), default));
        return Success(await store.CommitAsync(staged, new(), default));
    }
    private static async Task AssertContentAsync(IArtifactStore store, ArtifactStamp stamp)
    {
        await using var read = Success(await store.OpenReadAsync(new(stamp.Identity.Digest), new(), default));
        using var destination = new MemoryStream();
        Success(await read.CopyToAsync(destination, new(), default));
        Assert.Equal(Content, destination.ToArray());
    }
    private static MetadataArtifactEvidence Evidence(ArtifactMetadataFixtureSession session, ArtifactMutationReceipt receipt)
        => session.Publication.Encode(Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value);
    private static async Task CommitAsync(IMetadataStore store, params MetadataMutation[] mutations)
    {
        var ticket = MetadataSuccess(await store.ReserveOperationAsync(new(), default));
        MetadataSuccess(await store.CommitAsync(new(ticket, [.. mutations], new MetadataOption<MetadataLeaseGuard>.None()), new(), default));
    }
    private static T MetadataSuccess<T>(MetadataResult<T> result) where T : notnull
        => result is MetadataResult<T>.Success success ? success.Value
            : throw new Xunit.Sdk.XunitException(result is MetadataResult<T>.Failure failed ? $"Metadata failed: {failed.Code}." : "Metadata failed.");
    private static (MetadataRegistry, MetadataPackage) SeedRecords()
    {
        var registry = new MetadataRegistry
        {
            Id = new(Guid.NewGuid()),
            Ecosystem = new("nuget"),
            Upstream = new("https://packages.example.invalid/v3/"),
            Enabled = true,
            Label = new("synthetic artifact registry"),
            PolicyId = new MetadataOption<MetadataId>.None(),
            Secret = new MetadataOption<MetadataSecretReference>.None(),
            Revision = new(Guid.NewGuid())
        };
        return (registry, new MetadataPackage
        {
            Key = new(registry.Id, registry.Ecosystem, new("example.package")),
            Label = new("synthetic artifact package"),
            Revision = new(Guid.NewGuid())
        });
    }
    private static MetadataCacheEntry Entry(MetadataPackage package, ArtifactStamp stamp) => new()
    {
        Identity = new(package.Key.RegistryId, package.Key.Ecosystem, new("/flat/example/1.0.0"), "GET", new("anonymous")),
        Package = package.Key,
        Digest = stamp.Identity.Digest,
        Length = stamp.Identity.Length,
        Status = 200,
        Headers = new([]),
        Created = new(0),
        Validated = new(1),
        FreshUntil = new(253402300799999),
        Revision = new(Guid.NewGuid())
    };
}
