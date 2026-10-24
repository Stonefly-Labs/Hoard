using Hoard.Abstractions.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataConcurrencyAssertions
{
    public static async Task CompetingCreatesAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        var tickets = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ => await Ticket(store, cancellationToken)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => store.CommitAsync(
            Batch(ticket, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())), new(), cancellationToken).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(7, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(outcome => outcome.Code == MetadataFailureCode.Conflict));
        Assert.Single(await Traverse(store, Registries(), cancellationToken));
    }

    public static async Task RevisionRacesAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        var (registry, _) = await Seed(store, cancellationToken);
        var tickets = await Task.WhenAll(Enumerable.Range(0, 4).Select(async _ => await Ticket(store, cancellationToken)));
        var outcomes = await Task.WhenAll(tickets.Select((ticket, number) => store.CommitAsync(
            Batch(ticket, new MetadataMutation.PutRegistry(registry with { Label = new(number.ToString(System.Globalization.CultureInfo.InvariantCulture)) },
                new ExpectedRevision.Match(registry.Revision))), new(), cancellationToken).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(3, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(outcome => outcome.Code == MetadataFailureCode.Conflict));
        var package = Package(registry, "recreated");
        await Commit(store, cancellationToken, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        package = await Read<MetadataPackage>(store, package.Selector, cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeletePackage(package.Key, package.Revision));
        await Commit(store, cancellationToken, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        Assert.NotEqual(package.Revision, (await Read<MetadataPackage>(store, package.Selector, cancellationToken)).Revision);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.DeletePackage(package.Key, package.Revision)), new(), cancellationToken)));
    }
}
