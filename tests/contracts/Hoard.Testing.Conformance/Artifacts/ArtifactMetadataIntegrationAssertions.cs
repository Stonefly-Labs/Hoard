using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactMetadataIntegrationAssertions(
    IArtifactStore store, IMetadataStore metadata, ArtifactStoreIdentity identity,
    IArtifactCoordinationAuthority authority, Func<ArtifactCommitEvidence, MetadataArtifactEvidence> encode)
{
    public async Task ReferenceDuringDeletionAsync(Func<int> waitingAdmissions, CancellationToken cancellationToken)
    {
        var receipt = await PublishAsync(store, cancellationToken);
        var (registry, package) = SeedRecords();
        await CommitAsync(metadata, cancellationToken, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var operation = Guid.NewGuid();
        var request = new ArtifactProtectionRequest(operation, ArtifactProtectionOperation.Deletion,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        var exclusive = Success(await authority.AcquireAsync(request, new(), cancellationToken));
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await metadata.ReserveOperationAsync(new(), cancellationToken));
        var publishing = metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), cancellationToken).AsTask();
        try
        {
            await WaitForReferenceAdmissionAsync(waitingAdmissions, publishing);
            Assert.False(publishing.IsCompleted);
            await using var retained = Success(await authority.RetainAsync(exclusive, request, new(), cancellationToken));
            await exclusive.DisposeAsync();
            Assert.False(publishing.IsCompleted);
        }
        finally { await exclusive.DisposeAsync(); }
        MetadataSuccess(await publishing);
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(deletion, new(), cancellationToken)).Code);
        await AssertContentAsync(store, receipt.Stamp, cancellationToken);
    }

    private static async Task WaitForReferenceAdmissionAsync(Func<int> waitingAdmissions, Task publication)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        while (waitingAdmissions() == 0 && !publication.IsCompleted)
        {
            deadline.Token.ThrowIfCancellationRequested();
            await Task.Yield();
        }
        Assert.Equal(1, waitingAdmissions());
    }

    public async Task FailedTransactionAsync(CancellationToken cancellationToken)
    {
        var receipt = await PublishAsync(store, cancellationToken);
        var (_, package) = SeedRecords();
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await metadata.ReserveOperationAsync(new(), cancellationToken));
        var failed = await metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), cancellationToken);
        Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(failed);
        Assert.IsType<MetadataReadItem.NotFound>(MetadataSuccess(await metadata.ReadAsync(new([entry.Selector]), new(), cancellationToken)).Items[0]);
        var reconciled = Assert.IsType<ArtifactResolution.Committed>(Success(
            await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)));
        Assert.Equal(receipt, reconciled.Receipt);
        await AssertContentAsync(store, receipt.Stamp, cancellationToken);
    }

    public async Task ActualReferencesAsync(CancellationToken cancellationToken)
    {
        var receipt = await PublishAsync(store, cancellationToken);
        var (registry, package) = SeedRecords();
        await CommitAsync(metadata, cancellationToken, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var entry = Entry(package, receipt.Stamp);
        await CommitAsync(metadata, cancellationToken, new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(receipt)));
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(deletion, new(), cancellationToken)).Code);
        await AssertContentAsync(store, receipt.Stamp, cancellationToken);
        var current = Assert.IsType<MetadataCacheEntry>(Assert.IsType<MetadataReadItem.Found>(
            MetadataSuccess(await metadata.ReadAsync(new([entry.Selector]), new(), cancellationToken)).Items[0]).Record);
        await CommitAsync(metadata, cancellationToken, new MetadataMutation.DeleteCacheEntry(current.Identity, current.Revision));
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await store.DeleteAsync(deletion, new(), cancellationToken)).Outcome);
        var staleTicket = MetadataSuccess(await metadata.ReserveOperationAsync(new(), cancellationToken));
        Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await metadata.CommitAsync(new(staleTicket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), cancellationToken));
        Assert.IsType<MetadataReadItem.NotFound>(MetadataSuccess(await metadata.ReadAsync(new([entry.Selector]), new(), cancellationToken)).Items[0]);
    }

    public async Task LostAcknowledgmentProtectionAsync(
        Action blockCompletion, Func<Task> waitForCompletion, Action releaseCompletion,
        Func<Task> whenArtifactIdle, Func<Task> whenMetadataIdle, CancellationToken cancellationToken)
    {
        var receipt = await PublishAsync(store, cancellationToken);
        var (registry, package) = SeedRecords();
        await CommitAsync(metadata, cancellationToken, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        var entry = Entry(package, receipt.Stamp);
        var ticket = MetadataSuccess(await metadata.ReserveOperationAsync(new(), cancellationToken));
        blockCompletion();
        var committing = metadata.CommitAsync(new(ticket,
            [new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), Evidence(receipt))],
            new MetadataOption<MetadataLeaseGuard>.None()), new(TimeSpan.FromMilliseconds(150)), cancellationToken).AsTask();
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        try
        {
            await waitForCompletion().WaitAsync(TimeSpan.FromSeconds(2));
            var failed = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
                await committing.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(MetadataFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(30)), cancellationToken)).Code);
            await whenArtifactIdle().WaitAsync(TimeSpan.FromSeconds(2));
            await AssertContentAsync(store, receipt.Stamp, cancellationToken);
        }
        finally
        {
            releaseCompletion();
            await committing;
            await whenMetadataIdle();
        }
        Assert.IsType<MetadataResolution.Committed>(MetadataSuccess(await metadata.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(deletion, new(), cancellationToken)).Code);
    }

    private static readonly byte[] Content = "actual artifact metadata composition"u8.ToArray();
    private static async Task<ArtifactMutationReceipt> PublishAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource(Content);
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        return Success(await store.CommitAsync(staged, new(), cancellationToken));
    }
    private static async Task AssertContentAsync(IArtifactStore store, ArtifactStamp stamp, CancellationToken cancellationToken)
    {
        await using var read = Success(await store.OpenReadAsync(new(stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new MemoryStream();
        Success(await read.CopyToAsync(destination, new(), cancellationToken));
        Assert.Equal(Content, destination.ToArray());
    }
    private MetadataArtifactEvidence Evidence(ArtifactMutationReceipt receipt)
        => encode(Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value);
    private static async Task CommitAsync(IMetadataStore store, CancellationToken cancellationToken, params MetadataMutation[] mutations)
    {
        var ticket = MetadataSuccess(await store.ReserveOperationAsync(new(), cancellationToken));
        MetadataSuccess(await store.CommitAsync(new(ticket, [.. mutations], new MetadataOption<MetadataLeaseGuard>.None()), new(), cancellationToken));
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
