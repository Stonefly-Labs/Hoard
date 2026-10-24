using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataRelationshipTests
{
    [Fact]
    public async Task MP13_Explicit_final_graph_deletion_and_disabled_retention_are_atomic()
    {
        await using var fixture = await OpenAsync();
        await MetadataEntityAssertions.FinalGraphDeletionAndDisabledRetentionAsync(fixture.Store, CommonAuthority(fixture), default);
    }
}
