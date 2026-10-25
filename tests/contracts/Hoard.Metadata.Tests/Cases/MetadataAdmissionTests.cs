using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataAdmissionTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP32_Ordinary_use_requires_explicit_schema_admission()
    {
        await using var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        await MetadataAdmissionAssertions.ExplicitAdmissionAsync(
            fixture.Store, fixture.Schema, () => CommonCounters(fixture), default);
        ObserveOriginal(output, fixture, nameof(MetadataAdmissionTests));
    }

    [Fact]
    public async Task MP19_Invalid_budgets_and_closed_instances_do_not_dispatch_work()
    {
        var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        await MetadataAdmissionAssertions.InvalidBudgetsAsync(
            fixture.Store, fixture.Schema, () => CommonCounters(fixture), fixture.DisposeAsync, default);
        ObserveOriginal(output, fixture, nameof(MetadataAdmissionTests));
    }
}
