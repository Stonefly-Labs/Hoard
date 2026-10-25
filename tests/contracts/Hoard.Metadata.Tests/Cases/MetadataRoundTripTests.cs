using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataRoundTripTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes()
    {
        await using var fixture = await OpenAsync();
        var authority = CommonAuthority(fixture);
        await MetadataEntityAssertions.RoundTripAndInvalidRelationshipsAsync(fixture.Store, authority, default);
        ObserveOriginal(output, fixture, authority, nameof(MetadataRoundTripTests));
    }

    [Fact]
    public async Task MP05_Exact_bounds_and_overflow_reject_the_entire_candidate()
    {
        await using var fixture = await OpenAsync();
        await MetadataBoundsAssertions.ExactBoundsAsync(fixture.Store, default);
    }

    [Fact]
    public async Task MP06_Scopes_and_intervals_cannot_cross_registry_boundaries()
    {
        await using var fixture = await OpenAsync();
        await MetadataBoundsAssertions.ScopesAndIntervalsAsync(fixture.Store, default);
    }
}
