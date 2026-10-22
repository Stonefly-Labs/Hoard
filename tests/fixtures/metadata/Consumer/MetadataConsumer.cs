using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Consumer;

internal static class MetadataConsumer
{
    internal static async Task ExecuteAsync(IMetadataStore store, IMetadataSchemaAdministration schema)
    {
        static T Accepted<T>(MetadataResult<T> result) where T : notnull => result is MetadataResult<T>.Success success
            ? success.Value : throw new InvalidOperationException("Package-only consumer operation failed.");
        Accepted(await schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var id = new MetadataId(Guid.Parse("10000000-0000-0000-0000-000000000001"));
        var ticket = Accepted(await store.ReserveOperationAsync(new(), default));
        var registry = new MetadataRegistry
        {
            Id = id,
            Ecosystem = new("nuget"),
            Upstream = new("https://example.invalid/v3/"),
            Enabled = true,
            Label = new("synthetic consumer"),
            PolicyId = new MetadataOption<MetadataId>.None(),
            Secret = new MetadataOption<MetadataSecretReference>.None(),
            Revision = new(Guid.NewGuid())
        };
        var batch = new MetadataMutationBatch(ticket, [new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent())],
            new MetadataOption<MetadataLeaseGuard>.None());
        var receipt = Accepted(await store.CommitAsync(batch, new(), default));
        if (receipt.CommitId != Accepted(await store.CommitAsync(batch, new(), default)).CommitId
            || Accepted(await store.ReadAsync(new([registry.Selector]), new(), default)).Items.Single() is not MetadataReadItem.Found
            || await store.CommitAsync(new(ticket, [new MetadataMutation.PutRegistry(registry with { Enabled = false }, new ExpectedRevision.Absent())],
                new MetadataOption<MetadataLeaseGuard>.None()), new(), default) is not MetadataResult<MetadataCommitReceipt>.Failure { Code: MetadataFailureCode.Conflict })
        { throw new InvalidOperationException("Package-only consumer assertion failed."); }
    }
}
