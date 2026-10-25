using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactPublicationRaceTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Equivalent_concurrent_writers_keep_one_stamp_and_distinct_receipts(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.ConcurrentEquivalentWritersAsync(driver.Store,
            observer => SetObserver(driver, "publish.admitted", "object.publication-admitted", observer), default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationRaceTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Conflicting_staged_length_cannot_replace_valid_content_or_its_stamp(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.ConflictingStagedLengthAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationRaceTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Corrupt_existing_bytes_are_not_overwritten_or_reused(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.CorruptExistingContentAsync(driver.Store,
            () => driver.DamageOnlyPayload(truncate: false),
            bytes => File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes),
            default, ArtifactEvidenceTests.QuarantineReopen(driver));
    }
}
