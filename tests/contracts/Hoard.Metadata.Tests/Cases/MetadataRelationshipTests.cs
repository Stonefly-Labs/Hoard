using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataRelationshipTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP13_Explicit_final_graph_deletion_and_disabled_retention_are_atomic()
    {
        await using var fixture = await OpenAsync();
        var authority = CommonAuthority(fixture);
        await MetadataEntityAssertions.FinalGraphDeletionAndDisabledRetentionAsync(fixture.Store, authority, default);
        ObserveOriginal(output, fixture, authority, nameof(MetadataRelationshipTests));
    }
}
