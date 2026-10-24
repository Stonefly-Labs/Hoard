using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactEvidenceConsumerTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_receipt_assertion_rejects_wrong_receipt_acceptance_and_accepts_original_validator(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new AcceptsWrongReceipt(driver.Validator);
            var failure = await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() =>
                ArtifactEvidenceAssertions.ExactCurrentReceiptsAsync(
                    driver.Store, mutation, driver.Authority, driver.Identity, default));
            Assert.Contains("Assert.IsType()", failure.Message);
            Assert.Equal(2, mutation.Calls);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactEvidenceAssertions.ExactCurrentReceiptsAsync(
                driver.Store, driver.Validator, driver.Authority, driver.Identity, default);
        }
    }

    private sealed class AcceptsWrongReceipt(IArtifactEvidenceValidator validator) : IArtifactEvidenceValidator
    {
        public int Calls { get; private set; }
        public ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(
            ArtifactCommitEvidence evidence, IArtifactProtectionGuard protection,
            ArtifactCallOptions options, CancellationToken cancellationToken)
        {
            Calls++;
            return Calls == 2
                ? ValueTask.FromResult<ArtifactResult<ArtifactStamp>>(new ArtifactResult<ArtifactStamp>.Success(evidence.Stamp))
                : validator.ValidateAsync(evidence, protection, options, cancellationToken);
        }
    }
}
