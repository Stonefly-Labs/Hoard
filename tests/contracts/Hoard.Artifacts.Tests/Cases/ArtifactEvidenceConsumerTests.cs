using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactEvidenceConsumerTests
{
    [Theory]
    [InlineData("damaged-read")]
    [InlineData("committed-detection")]
    [InlineData("corrupt-existing")]
    public async Task Shared_quarantine_consumers_reject_lost_reopen_denial_and_accept_original_store(string consumer)
    {
        static Task CheckAsync(ArtifactProviderDriver driver, string consumer, ArtifactQuarantineReopen reopen)
        {
            string? path = null;
            if (consumer == "damaged-read")
            {
                return ArtifactReadAssertions.DamagedReadAsync(
                    driver.Store, driver.Validator, driver.Authority, driver.Identity, false,
                    () =>
                    {
                        path = Directory.GetFiles(driver.PayloadDirectory).Single();
                        return ValueTask.FromResult(File.ReadAllBytes(path));
                    },
                    truncate => { driver.DamageOnlyPayload(truncate); return ValueTask.CompletedTask; },
                    bytes =>
                    {
                        File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not captured."), bytes);
                        return ValueTask.CompletedTask;
                    }, default, reopen);
            }
            if (consumer == "committed-detection")
            {
                return ArtifactReadAssertions.CommittedDetectionQuarantineAsync(
                    driver.Store, "open", ArtifactDurability.LocalProcessCrash,
                    () =>
                    {
                        path = Directory.GetFiles(driver.PayloadDirectory).Single();
                        File.Delete(path);
                    },
                    bytes => File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not removed."), bytes),
                    () => throw new InvalidOperationException("Open detection does not observe publication."),
                    () => throw new InvalidOperationException("Open detection does not remove publication observation."),
                    () => throw new InvalidOperationException("Open detection does not mutate committed bytes."),
                    _ => throw new InvalidOperationException("Open detection restores its removed payload."),
                    default, reopen);
            }
            if (consumer == "corrupt-existing")
            {
                return ArtifactPublicationAssertions.CorruptExistingContentAsync(driver.Store,
                    () => driver.DamageOnlyPayload(truncate: false),
                    bytes => File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes),
                    default, reopen);
            }
            throw new ArgumentException("Unknown quarantine consumer.");
        }

        await using (var driver = await ArtifactProviderDriver.CreateAsync("local"))
        {
            var created = 0;
            LostReopenDenial? mutation = null;
            var reopen = new ArtifactQuarantineReopen((IArtifactStoreLifetime)driver.Store,
                driver.Identity, driver.Authority, () =>
                {
                    created++;
                    var store = new LocalArtifactStore(Path.GetDirectoryName(driver.PayloadDirectory)!);
                    mutation = new LostReopenDenial(store);
                    return (mutation, store);
                });
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() => CheckAsync(driver, consumer, reopen));
            Assert.Equal(1, created);
            Assert.NotNull(mutation);
            Assert.Equal(1, mutation.ActualCorruptFailures);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync("local"))
        {
            var created = 0;
            var reopen = new ArtifactQuarantineReopen((IArtifactStoreLifetime)driver.Store,
                driver.Identity, driver.Authority, () =>
                {
                    created++;
                    var store = new LocalArtifactStore(Path.GetDirectoryName(driver.PayloadDirectory)!);
                    return (store, store);
                });
            await CheckAsync(driver, consumer, reopen);
            Assert.Equal(1, created);
            Assert.True(driver.Ready);
        }
    }

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

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_damaged_read_assertion_rejects_revived_evidence_and_accepts_original_validator(string provider)
    {
        static Task CheckAsync(ArtifactProviderDriver driver, IArtifactEvidenceValidator validator)
        {
            string? path = null;
            return ArtifactReadAssertions.DamagedReadAsync(
                driver.Store, validator, driver.Authority, driver.Identity, false,
                () =>
                {
                    path = Directory.GetFiles(driver.PayloadDirectory).Single();
                    return ValueTask.FromResult(File.ReadAllBytes(path));
                },
                truncate => { driver.DamageOnlyPayload(truncate); return ValueTask.CompletedTask; },
                bytes =>
                {
                    File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not captured."), bytes);
                    return ValueTask.CompletedTask;
                }, default);
        }

        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new RevivedCorruptEvidence(driver.Validator);
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() => CheckAsync(driver, mutation));
            Assert.Equal(1, mutation.Calls);
            Assert.Equal(1, mutation.ActualCorruptFailures);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await CheckAsync(driver, driver.Validator);
        }
    }

    private sealed class LostReopenDenial(IArtifactStore store) : ArtifactPublicationConsumerTests.ForwardingStore(store)
    {
        public int ActualCorruptFailures { get; private set; }
        public override async ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
            ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct)
        {
            var result = await Store.OpenReadAsync(request, options, ct);
            if (result is not ArtifactResult<IArtifactReadSession>.Failure { Code: ArtifactFailureCode.CorruptContent } failed)
            { throw new InvalidOperationException("Mutation requires an actual reopened quarantine denial."); }
            ActualCorruptFailures++;
            return new ArtifactResult<IArtifactReadSession>.Failure(
                ArtifactFailureCode.NotFound, failed.Phase, failed.Action, failed.CorrelationId, failed.Ticket, failed.Cleanup);
        }
    }

    private sealed class RevivedCorruptEvidence(IArtifactEvidenceValidator validator) : IArtifactEvidenceValidator
    {
        public int Calls { get; private set; }
        public int ActualCorruptFailures { get; private set; }
        public async ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(
            ArtifactCommitEvidence evidence, IArtifactProtectionGuard protection,
            ArtifactCallOptions options, CancellationToken cancellationToken)
        {
            Calls++;
            var result = await validator.ValidateAsync(evidence, protection, options, cancellationToken);
            if (result is ArtifactResult<ArtifactStamp>.Failure { Code: ArtifactFailureCode.CorruptContent })
            {
                ActualCorruptFailures++;
                return new ArtifactResult<ArtifactStamp>.Success(evidence.Stamp);
            }
            throw new InvalidOperationException("Mutation requires an actual quarantined evidence failure.");
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
