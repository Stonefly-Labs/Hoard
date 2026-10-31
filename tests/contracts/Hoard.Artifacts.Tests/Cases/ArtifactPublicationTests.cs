using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactPublicationTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Empty_content_and_true_absence_are_distinct(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.EmptyContentAndAbsenceAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Empty_unknown_length_and_positive_short_reads_require_real_eof(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Every_expectation_is_checked_and_declared_length_does_not_replace_eof(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.EveryExpectationAndEofAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Unsupported_checksum_and_range_reject_before_storage_or_stream_io(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.UnsupportedChecksumAndRangeAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Staging_is_private_until_complete_verified_commit(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await using var barrier = new ArtifactTestBarrier("prefix");
        SetObserver(driver, "stage.prefix", "multipart.part", () => new(barrier.HoldAsync()));
        await ArtifactPublicationAssertions.PrivateStagingAsync(driver.Store,
            token => barrier.Entered.WaitAsync(token), barrier.Release, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Submitted_duplicates_are_fully_verified_and_keep_one_immutable_incarnation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactPublicationAssertions.VerifiedDuplicatesAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactPublicationTests));
    }

    internal static T Success<T>(ArtifactResult<T> result) where T : notnull
        => Assert.IsType<ArtifactResult<T>.Success>(result).Value;

    internal static Task<ArtifactMutationReceipt> PublishAsync(
        ArtifactProviderDriver driver, Stream source, ArtifactExpectations expectations) =>
        ArtifactPublicationAssertions.PublishAsync(driver.Store, source, expectations, default);

    internal static Task<byte[]> ReadAsync(ArtifactProviderDriver driver, ArtifactStamp stamp) =>
        ArtifactPublicationAssertions.ReadAsync(driver.Store, stamp, default);

    internal static void SetObserver(ArtifactProviderDriver driver, string localPoint, string objectPoint, Func<ValueTask> observer)
    {
        if (driver.LocalControls is { } local) { local.SetObserver(localPoint, observer); }
        else { driver.ObjectControls!.SetObserver(objectPoint, observer); }
    }

    internal sealed class ShortSource(byte[] bytes) : ArtifactPublicationAssertions.ShortSource(bytes);
}
