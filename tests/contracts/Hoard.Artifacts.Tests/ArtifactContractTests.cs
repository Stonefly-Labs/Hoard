using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Providers;
using Hoard.Abstractions.Storage;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactContractTests
{
    private static ArtifactStoreIdentity Store() => new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
    private static readonly ArtifactDigest Digest = new(new string('a', 64));
    private static ArtifactStamp Stamp() => new(Store(), new ArtifactIdentity(Digest, 1), Guid.NewGuid());
    private static ArtifactOperationTicket Ticket(ArtifactStoreIdentity store, ArtifactOperationKind kind)
        => new(store, Guid.NewGuid(), kind, DateTimeOffset.UnixEpoch, DateTimeOffset.UnixEpoch.AddHours(24), new string('a', 64));

    [Fact]
    public void Marker_and_historical_digest_remain_separate_from_operational_contracts()
    {
        Assert.Empty(typeof(IArtifactProvider).GetMethods());
        Assert.Equal([typeof(IHoardProvider)], typeof(IArtifactProvider).GetInterfaces());
        Assert.Equal("Hoard.Abstractions.Metadata", typeof(ArtifactDigest).Namespace);
        Assert.False(typeof(IArtifactStore).IsAssignableFrom(typeof(IArtifactProvider)));
        Assert.Equal(9, typeof(IArtifactStore).GetMethods().Count(method => !method.IsSpecialName));
        Assert.Equal(2, typeof(IArtifactCoordinationAuthority).GetMethods().Length);
        Assert.Empty(typeof(IArtifactStore).GetInterfaces());
        Assert.Empty(typeof(IArtifactMaintenance).GetInterfaces());
    }

    [Fact]
    public void Ranges_and_completion_reject_overflow_mismatched_digest_or_length()
    {
        Assert.Equal(long.MaxValue - 1, new ArtifactReadMode.Range(long.MaxValue - 1, 1).Offset);
        foreach (var (offset, count) in new[] { (-1L, 1L), (0L, 0L), (long.MaxValue, 1L), (1L, long.MaxValue) })
        { Assert.Throws<ArgumentException>(() => new ArtifactReadMode.Range(offset, count)); }
        var stamp = Stamp();
        Assert.NotNull(new ArtifactReadCompletion(stamp, Digest, 1));
        Assert.Throws<ArgumentException>(() => new ArtifactReadCompletion(stamp, Digest, 0));
        var different = new ArtifactDigest(new string('b', 64));
        Assert.Throws<ArgumentException>(() => new ArtifactReadRequest(different,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)));
    }

    [Fact]
    public void Protection_requires_exact_matching_scope_and_positive_grant_identity()
    {
        var stamp = Stamp();
        var id = Guid.NewGuid();
        var request = new ArtifactProtectionRequest(id, ArtifactProtectionOperation.Read, stamp.Store, Digest);
        Assert.Equal(ArtifactProtectionMode.Shared, request.Mode);
        foreach (var operation in new[] { ArtifactProtectionOperation.Reference, ArtifactProtectionOperation.Deletion })
        {
            Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(id, operation, stamp.Store, Digest));
            Assert.NotNull(new ArtifactProtectionRequest(id, operation, stamp.Store, Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)));
        }
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(id, ArtifactProtectionOperation.Read,
            Store(), Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(Guid.Empty, ArtifactProtectionOperation.Read, stamp.Store, Digest));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionGrant(id, request, 0, DateTimeOffset.UnixEpoch.AddMinutes(1)));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionGrant(Guid.Empty, request, 1, DateTimeOffset.UnixEpoch.AddMinutes(1)));
        Assert.NotNull(new ArtifactProtectionGrant(id, request, 1, DateTimeOffset.UnixEpoch.AddMinutes(1)));
    }

    [Fact]
    public void Receipts_cannot_mix_stores_kinds_visibility_evidence_or_resolution()
    {
        var stamp = Stamp();
        var ticket = Ticket(stamp.Store, ArtifactOperationKind.Write);
        var receiptId = Guid.NewGuid();
        var proof = new ArtifactCommitEvidence(stamp, ticket.Id, receiptId, "opaque", ArtifactPublicationOutcome.Published);
        var receipt = new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Published, stamp,
            ArtifactVisibility.Committed, ArtifactReclamation.NotApplicable, new ArtifactOption<ArtifactCommitEvidence>.Some(proof));
        Assert.Equal(receipt, new ArtifactResolution.Committed(receipt).Receipt);
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.Removed(receipt));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Published,
            stamp, ArtifactVisibility.Committed, ArtifactReclamation.NotApplicable));
        var delete = Ticket(stamp.Store, ArtifactOperationKind.Delete);
        var removed = new ArtifactMutationReceipt(delete, receiptId, ArtifactMutationOutcome.Removed, stamp,
            ArtifactVisibility.Removed, ArtifactReclamation.Pending);
        Assert.NotNull(new ArtifactResolution.Removed(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.Committed(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.AlreadyAbsent(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(delete, receiptId, ArtifactMutationOutcome.Removed,
            Stamp(), ArtifactVisibility.Removed, ArtifactReclamation.Pending));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Removed,
            stamp, ArtifactVisibility.Removed, ArtifactReclamation.Pending));
    }

    [Fact]
    public void Recovery_and_cleanup_are_bounded_immutable_exact_targets_not_absence_authority()
    {
        var stamp = Stamp();
        Assert.NotNull(new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All, 100));
        foreach (var size in new[] { 0, 101 })
        { Assert.Throws<ArgumentException>(() => new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All, size)); }
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All,
            continuation: new ArtifactOption<string>.Some(new string('x', 4097))));
        var observation = new ArtifactRecoveryObservation(ArtifactObservationKind.Committed, Guid.NewGuid(),
            new ArtifactOption<ArtifactStamp>.Some(stamp));
        var inputs = new List<ArtifactRecoveryObservation> { observation };
        var page = new ArtifactRecoveryPage(inputs, ArtifactEnumerationConsistency.Incomplete);
        inputs.Clear();
        Assert.Single(page.Observations);
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryPage(Enumerable.Repeat(observation, 101), ArtifactEnumerationConsistency.Snapshot));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryPage(default(ImmutableArray<ArtifactRecoveryObservation>), ArtifactEnumerationConsistency.Snapshot));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryObservation(ArtifactObservationKind.Committed, Guid.NewGuid()));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryObservation(ArtifactObservationKind.ActiveStaging, Guid.NewGuid()));
        ArtifactCleanupTarget target = new ArtifactCleanupTarget.RemovedIncarnation(stamp);
        Assert.NotNull(new ArtifactCleanupRequest(stamp.Store, [target]));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(Store(), [target]));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(stamp.Store, []));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(stamp.Store, Enumerable.Repeat(target, 101)));
        Assert.NotNull(new ArtifactCleanupReport(100, 0, 0, 0));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupReport(100, 1, 0, 0));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupReport(0, 0, 0, -1));
    }

    [Fact]
    public void Failures_shutdown_and_qualification_cannot_be_success_shaped()
    {
        var id = Guid.NewGuid();
        Assert.Throws<ArgumentNullException>(() => new ArtifactResult<ArtifactIdentity>.Success(null!));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            (ArtifactFailureCode)99, ArtifactPhase.Read, ArtifactAction.None, id));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            ArtifactFailureCode.Uncertain, ArtifactPhase.Publication, ArtifactAction.ReconcileExactTicket, id));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, ArtifactAction.OperatorRecovery, id));
        Assert.NotNull(new ArtifactShutdown(ArtifactCleanupState.RetainedLiveOwnership, 1, 1, false));
        Assert.Throws<ArgumentException>(() => new ArtifactShutdown(ArtifactCleanupState.Released, 1, 0, false));
        Assert.Throws<ArgumentException>(() => new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, true));
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits());
        Assert.True(capabilities.MeetsBaseline);
        Assert.False(new ArtifactCapabilities(2, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits()).MeetsBaseline);
        var cases = Enumerable.Range(1, 48).Select(number => $"AS-{number:D2}").ToArray();
        var hash = new string('a', 64);
        var environment = new ArtifactQualificationEnvironment("test OS", "test runtime", "test filesystem", "test flush");
        var results = cases.Select(id => new ArtifactQualificationCaseResult(id,
            id is "AS-41" or "AS-42" or "AS-43" or "AS-44"
                ? ArtifactQualificationCaseStatus.NotApplicable : ArtifactQualificationCaseStatus.Passed,
            TimeSpan.Zero, [hash])).ToArray();
        Assert.NotNull(new ArtifactQualificationRecord("fixture.artifact", "0.1.0", hash, hash, hash, hash,
            environment, capabilities, results));
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationRecord("fixture.artifact", "0.1.0", hash, hash, hash, hash,
            environment, capabilities, results.Take(47)));
    }

    [Fact]
    public void Qualification_exclusions_cannot_exchange_simulated_and_durable_failure_models()
    {
        var hash = new string('a', 64);
        var cases = Enumerable.Range(1, 48).Select(number => $"AS-{number:D2}").ToArray();
        var durable = new ArtifactCapabilities(1, ArtifactDurability.LocalProcessCrash,
            ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits());
        var simulated = new ArtifactCapabilities(1, ArtifactDurability.SimulationOnly,
            ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits());
        var exclusions = new[] { "AS-41", "AS-42", "AS-43", "AS-44" };
        var environment = new ArtifactQualificationEnvironment("test OS", "test runtime", "test filesystem", "test flush");
        ArtifactQualificationRecord Record(ArtifactCapabilities capabilities, IEnumerable<string> omitted) =>
            new("fixture.artifact", "0.1.0", hash, hash, hash, hash, environment, capabilities,
                cases.Select(id => new ArtifactQualificationCaseResult(id, omitted.Contains(id)
                    ? ArtifactQualificationCaseStatus.NotApplicable : ArtifactQualificationCaseStatus.Passed, TimeSpan.Zero, [hash])));
        Assert.Empty(Record(durable, []).Exclusions);
        Assert.Equal(exclusions, Record(simulated, exclusions).Exclusions);
        Assert.Throws<ArgumentException>(() => Record(durable, exclusions));
        foreach (var partial in new[] { Array.Empty<string>(), new[] { "AS-41" }, exclusions[..3] })
        { Assert.Throws<ArgumentException>(() => Record(simulated, partial)); }
    }

    [Fact]
    public void Flat_case_names_and_unattributed_hashes_cannot_claim_qualification()
    {
        var hash = new string('a', 64);
        var cases = Enumerable.Range(1, 48).Select(number => $"AS-{number:D2}");
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.SimulationOnly,
            ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits());
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationRecord(
            "fixture.artifact", "0.1.0", hash, hash, hash, hash, hash,
            capabilities, cases, [hash], ["AS-41", "AS-42", "AS-43", "AS-44"]));
    }

    [Fact]
    public void Qualification_case_results_reject_missing_or_unbounded_attribution()
    {
        var hash = new string('a', 64);
        Assert.NotNull(new ArtifactQualificationCaseResult("AS-48", ArtifactQualificationCaseStatus.Passed, TimeSpan.Zero, [hash]));
        foreach (var id in new[] { "", "AS-00", "AS-49", "AS-1", "as-01", "AS-+1" })
        {
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationCaseResult(
                id, ArtifactQualificationCaseStatus.Passed, TimeSpan.Zero, [hash]));
        }
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationCaseResult(
            "AS-01", (ArtifactQualificationCaseStatus)99, TimeSpan.Zero, [hash]));
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationCaseResult(
            "AS-01", ArtifactQualificationCaseStatus.Passed, TimeSpan.FromTicks(-1), [hash]));
        foreach (var proofs in new[] { Array.Empty<string>(), new[] { hash, hash }, new[] { "foreign" },
            Enumerable.Range(0, 33).Select(index => index.ToString("x64")).ToArray() })
        {
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationCaseResult(
                "AS-01", ArtifactQualificationCaseStatus.Passed, TimeSpan.Zero, proofs));
        }
        Assert.NotNull(new ArtifactQualificationCaseResult("AS-01", ArtifactQualificationCaseStatus.Passed,
            TimeSpan.Zero, Enumerable.Range(0, 32).Select(index => index.ToString("x64"))));
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationCaseResult(
            "AS-01", ArtifactQualificationCaseStatus.Passed, TimeSpan.Zero, default(ImmutableArray<string>)));
    }

    [Fact]
    public void Qualification_records_keep_case_proofs_and_environment_attributable_and_immutable()
    {
        var hash = new string('a', 64);
        var other = new string('b', 64);
        var proofInputs = new List<string> { hash };
        var first = new ArtifactQualificationCaseResult("AS-01", ArtifactQualificationCaseStatus.Passed,
            TimeSpan.Zero, proofInputs);
        var results = Enumerable.Range(2, 47).Select(number => new ArtifactQualificationCaseResult(
            $"AS-{number:D2}", ArtifactQualificationCaseStatus.Passed, TimeSpan.FromMilliseconds(1), [other]))
            .Prepend(first).ToList();
        var environment = new ArtifactQualificationEnvironment("test OS", "test runtime", "test filesystem", "test flush");
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.LocalProcessCrash,
            ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits());
        ArtifactQualificationRecord Record(IEnumerable<ArtifactQualificationCaseResult> input, ArtifactCapabilities? selected = null)
            => new("fixture.artifact", "0.1.0", hash, hash, hash, hash, environment, selected ?? capabilities, input);
        var record = Record(results);
        proofInputs[0] = other;
        Assert.Equal(hash, record.CaseResults[0].ProofHashes[0]);
        Assert.Equal(other, record.CaseResults[1].ProofHashes[0]);
        Assert.Equal(new[] { hash, other }, record.ProofHashes);
        Assert.Equal(environment.Sha256, record.EnvironmentSha256);
        Assert.NotEqual(environment.Sha256,
            new ArtifactQualificationEnvironment("test OS", "other runtime", "test filesystem", "test flush").Sha256);
        Assert.Throws<ArgumentException>(() => Record(results.Take(47)));
        Assert.Throws<ArgumentException>(() => Record(results.Append(first)));
        Assert.Throws<ArgumentException>(() => Record(results.Take(47).Append(first)));
        Assert.Throws<ArgumentException>(() => Record(results.Skip(1).Prepend(new(
            "AS-01", ArtifactQualificationCaseStatus.NotApplicable, TimeSpan.Zero, [hash]))));
        Assert.Throws<ArgumentException>(() => Record(results.Select((result, index) => new ArtifactQualificationCaseResult(
            result.CaseId, result.Status, result.Duration, Enumerable.Range(index * 6, 6).Select(value => value.ToString("x64"))))));
        Assert.Throws<ArgumentException>(() => Record(results, new(2, ArtifactDurability.LocalProcessCrash,
            ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits())));
        Assert.Throws<ArgumentException>(() => Record(results, new(1, ArtifactDurability.LocalProcessCrash,
            ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits(), conditionalPublication: false)));
        results.Clear();
        Assert.Equal(48, record.CaseResults.Length);
    }

    [Fact]
    public void Qualification_environment_is_bounded_unambiguous_and_redacted()
    {
        Assert.NotNull(new ArtifactQualificationEnvironment(new string('x', 256), "runtime", "filesystem", "flush"));
        foreach (var label in new[] { "", "   ", "line\nbreak", "nul\0", new string('x', 257) })
        {
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationEnvironment(label, "runtime", "filesystem", "flush"));
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationEnvironment("OS", label, "filesystem", "flush"));
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationEnvironment("OS", "runtime", label, "flush"));
            Assert.Throws<ArgumentException>(() => new ArtifactQualificationEnvironment("OS", "runtime", "filesystem", label));
        }
        Assert.Throws<ArgumentNullException>(() => new ArtifactQualificationEnvironment(null!, "runtime", "filesystem", "flush"));
        ArtifactTestData.AssertSanitized(new ArtifactQualificationEnvironment(
            ArtifactTestData.Canary, "runtime", "filesystem", "flush").ToString());
    }
}
