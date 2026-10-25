using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataSchemaTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP33_Unrelated_and_partial_layouts_are_not_empty_or_permission_to_create()
    {
        var observations = new OriginalObservationSequence(output, nameof(MetadataSchemaTests));
        foreach (var partial in new[] { false, true })
        {
            await using var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
            await MetadataSchemaAssertions.UnrecognizedLayoutAsync(new OriginalMetadataSchemaSession(fixture, observations), partial, default);
        }
    }

    [Fact]
    public async Task MP32_Old_schema_requires_explicit_authorized_upgrade_and_preserves_records()
    {
        var clock = new MetadataTestClock();
        await using var initial = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        var observations = new OriginalObservationSequence(output, nameof(MetadataSchemaTests));
        await MetadataSchemaAssertions.UpgradeAsync(new OriginalMetadataSchemaSession(initial, observations), default);
    }

    [Fact]
    public async Task MP33_Future_schema_and_recognized_corruption_are_never_created_over()
    {
        await using var original = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        await using var corrupt = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        var observations = new OriginalObservationSequence(output, nameof(MetadataSchemaTests));
        await MetadataSchemaAssertions.FutureAndCorruptAsync(
            new OriginalMetadataSchemaSession(original, observations), new OriginalMetadataSchemaSession(corrupt, observations), default);
    }

    [Fact]
    public async Task MP34_Unsupported_and_foreign_upgrade_authorizations_leave_old_state_unchanged()
    {
        var clock = new MetadataTestClock();
        await using var original = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        var observations = new OriginalObservationSequence(output, nameof(MetadataSchemaTests));
        await MetadataSchemaAssertions.InvalidUpgradeAsync(new OriginalMetadataSchemaSession(original, observations), default);
    }

    [Fact]
    public async Task MP35_Upgrade_exclusion_prevents_partial_admission_and_has_one_winner()
    {
        var clock = new MetadataTestClock();
        await using var original = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        var observations = new OriginalObservationSequence(output, nameof(MetadataSchemaTests));
        await MetadataSchemaAssertions.UpgradeExclusionAsync(new OriginalMetadataSchemaSession(original, observations), default);
    }
}
