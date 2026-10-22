using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactEvidenceTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Only_exact_current_receipts_with_opaque_same_operation_protection_validate(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("attributable evidence"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            driver.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        var protection = Success(await driver.Authority.AcquireAsync(request, new(), default));
        try
        {
            Assert.Equal(receipt.Stamp, Success(await driver.Validator.ValidateAsync(proof, protection, new(), default)));
            var wrong = new ArtifactCommitEvidence(proof.Stamp, proof.TicketId, Guid.NewGuid(), proof.ProofHandle, proof.Outcome);
            Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await driver.Validator.ValidateAsync(wrong, protection, new(), default));
            await using var copied = new CopiedGuard(protection.Grant);
            Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, copied, new(), default)).Code);
            var foreignStamp = new ArtifactStamp(new ArtifactStoreIdentity(driver.Identity.ProviderModuleId,
                driver.Identity.InstanceId, Guid.NewGuid()), proof.Stamp.Identity, proof.Stamp.Incarnation);
            var foreign = new ArtifactCommitEvidence(foreignStamp, proof.TicketId, proof.ReceiptId, proof.ProofHandle, proof.Outcome);
            Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await driver.Validator.ValidateAsync(foreign, protection, new(), default));
        }
        finally { await protection.DisposeAsync(); }
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
            await driver.Validator.ValidateAsync(proof, protection, new(), default)).Code);
    }

    private sealed class CopiedGuard(ArtifactProtectionGrant grant) : IArtifactProtectionGuard
    {
        public ArtifactProtectionGrant Grant => grant;
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
