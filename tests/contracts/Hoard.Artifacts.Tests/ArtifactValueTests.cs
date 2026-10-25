using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Artifacts.Tests;

public sealed partial class ArtifactValueTests
{
    partial void ObserveIdentityContract();
    private static readonly ArtifactDigest Digest = new(new string('a', 64));
    private static ArtifactStoreIdentity Store() => new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
    private static ArtifactOperationTicket Ticket() => new(Store(), Guid.NewGuid(), ArtifactOperationKind.Write,
        DateTimeOffset.UnixEpoch, DateTimeOffset.UnixEpoch.AddHours(24), new string('a', 64));

    [Fact]
    public void Identity_bounds_preserve_empty_and_reject_overflow_negative_or_null()
    {
        Assert.Equal(0, new ArtifactIdentity(Digest, 0).Length);
        Assert.Equal(ArtifactLimits.MaximumArtifactBytes, new ArtifactIdentity(Digest, ArtifactLimits.MaximumArtifactBytes).Length);
        Assert.Equal(3, new ArtifactIdentity(Digest, 3, 3).Length);
        foreach (var length in new[] { -1L, long.MaxValue, ArtifactLimits.MaximumArtifactBytes + 1 })
        { Assert.Throws<ArgumentException>(() => new ArtifactIdentity(Digest, length)); }
        Assert.Throws<ArgumentException>(() => new ArtifactIdentity(Digest, 4, 3));
        Assert.Throws<ArgumentException>(() => new ArtifactIdentity(Digest, 0, 0));
        Assert.Throws<ArgumentNullException>(() => new ArtifactIdentity(null!, 0));
        ObserveIdentityContract();
    }

    [Fact]
    public void Store_stamp_and_handles_reject_empty_foreign_components_and_unsafe_text()
    {
        var id = Guid.NewGuid();
        foreach (var valid in new[] { "a", "0", "fixture.artifact-1", new string('a', 128) })
        { Assert.Equal(valid, new ArtifactStoreIdentity(valid, id, id).ProviderModuleId); }
        foreach (var invalid in new[] { "", "A", "../escape", "a..b", "a/b", "a b", "é", new string('a', 129) })
        { Assert.Throws<ArgumentException>(() => new ArtifactStoreIdentity(invalid, id, id)); }
        Assert.Throws<ArgumentException>(() => new ArtifactStoreIdentity("a", Guid.Empty, id));
        Assert.Throws<ArgumentException>(() => new ArtifactStoreIdentity("a", id, Guid.Empty));
        var identity = new ArtifactIdentity(Digest, 0);
        Assert.NotNull(new ArtifactStamp(Store(), identity, id));
        Assert.Throws<ArgumentException>(() => new ArtifactStamp(Store(), identity, Guid.Empty));
        var stamp = new ArtifactStamp(Store(), identity, id);
        Assert.NotNull(new ArtifactCommitEvidence(stamp, id, id, new string('x', 4096), ArtifactPublicationOutcome.Published));
        foreach (var invalid in new[] { "", "a b", "\0", "é", new string('a', 4097) })
        { Assert.Throws<ArgumentException>(() => new ArtifactCommitEvidence(stamp, id, id, invalid, ArtifactPublicationOutcome.Published)); }
        Assert.Throws<ArgumentException>(() => new ArtifactCommitEvidence(stamp, id, id, "safe", (ArtifactPublicationOutcome)99));
    }

    [Fact]
    public void Expectations_and_checksums_copy_input_and_reject_each_bound()
    {
        var bytes = new byte[64];
        var checksum = new ArtifactChecksumExpectation("sha512", bytes);
        bytes[0] = 7;
        Assert.Equal(0, checksum.Digest[0]);
        Assert.Equal(0, new ArtifactExpectations(1, exactLength: new ArtifactOption<long>.Some(0))
            .ExactLength is ArtifactOption<long>.Some expectedLength ? expectedLength.Value : -1);
        foreach (var cap in new[] { 0L, -1, long.MaxValue })
        { Assert.Throws<ArgumentException>(() => new ArtifactExpectations(cap)); }
        foreach (var length in new[] { -1L, 2 })
        { Assert.Throws<ArgumentException>(() => new ArtifactExpectations(1, exactLength: new ArtifactOption<long>.Some(length))); }
        foreach (var algorithm in new[] { "", "é", "a\n", new string('a', 17) })
        { Assert.Throws<ArgumentException>(() => new ArtifactChecksumExpectation(algorithm, [1])); }
        Assert.Throws<ArgumentException>(() => new ArtifactChecksumExpectation("sha512", []));
        Assert.Throws<ArgumentException>(() => new ArtifactChecksumExpectation("sha512", new byte[65]));
        Assert.NotNull(new ArtifactChecksumExpectation("unknown", [1]));
        Assert.Throws<ArgumentNullException>(() => new ArtifactOption<ArtifactDigest>.Some(null!));
    }

    [Fact]
    public void Tickets_and_staging_validate_lifetime_kind_fingerprint_generation_and_expiry()
    {
        var ticket = Ticket();
        Assert.Equal(TimeSpan.FromHours(24), ticket.Expires - ticket.Issued);
        Assert.Throws<ArgumentException>(() => new ArtifactOperationTicket(ticket.Store, Guid.Empty, ticket.Kind,
            ticket.Issued, ticket.Expires, ticket.IntentFingerprint));
        Assert.Throws<ArgumentException>(() => new ArtifactOperationTicket(ticket.Store, ticket.Id, (ArtifactOperationKind)99,
            ticket.Issued, ticket.Expires, ticket.IntentFingerprint));
        Assert.Throws<ArgumentException>(() => new ArtifactOperationTicket(ticket.Store, ticket.Id, ticket.Kind,
            ticket.Issued, ticket.Issued.AddHours(23), ticket.IntentFingerprint));
        Assert.Throws<ArgumentException>(() => new ArtifactOperationTicket(ticket.Store, ticket.Id, ticket.Kind,
            ticket.Issued, ticket.Expires, "../foreign"));
        var id = Guid.NewGuid();
        Assert.NotNull(new ArtifactStagingOwner(ticket, id, id, 1, ticket.Issued.AddSeconds(30)));
        foreach (var generation in new[] { 0L, -1 })
        { Assert.Throws<ArgumentException>(() => new ArtifactStagingOwner(ticket, id, id, generation, ticket.Issued.AddSeconds(30))); }
        Assert.Throws<ArgumentException>(() => new ArtifactStagingOwner(ticket, Guid.Empty, id, 1, ticket.Issued.AddSeconds(30)));
        Assert.Throws<ArgumentException>(() => new ArtifactStagingOwner(ticket, id, id, 1, ticket.Issued));
        Assert.Throws<ArgumentException>(() => new ArtifactStagingOwner(ticket, id, id, 1, ticket.Expires.AddSeconds(1)));
    }

    [Fact]
    public void Finite_options_reject_zero_submillisecond_and_excessive_deadlines()
    {
        Assert.Equal(TimeSpan.FromMilliseconds(1), new ArtifactCallOptions(TimeSpan.FromMilliseconds(1)).Deadline);
        Assert.Equal(TimeSpan.FromSeconds(30), new ArtifactCallOptions(TimeSpan.FromSeconds(30)).Deadline);
        foreach (var invalid in new[] { TimeSpan.Zero, TimeSpan.FromTicks(1), TimeSpan.FromSeconds(31), TimeSpan.MinValue })
        { Assert.Throws<ArgumentException>(() => new ArtifactCallOptions(invalid)); }
        Assert.Throws<ArgumentException>(() => new ArtifactTransferOptions(TimeSpan.FromMinutes(31)));
        Assert.Throws<ArgumentException>(() => new ArtifactTransferOptions(inactivity: TimeSpan.FromMinutes(3)));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupOptions(TimeSpan.FromSeconds(31)));
        Assert.Throws<ArgumentException>(() => new ArtifactMaintenanceOptions(TimeSpan.FromMinutes(3)));
        Assert.Throws<ArgumentException>(() => new ArtifactOwnershipOptions(TimeSpan.FromMinutes(3)));
        Assert.Throws<ArgumentException>(() => new ArtifactOwnershipOptions(renewal: TimeSpan.FromSeconds(11)));
        Assert.NotNull(new ArtifactTransferOptions(TimeSpan.FromMinutes(30), TimeSpan.FromMinutes(2)));
        Assert.NotNull(new ArtifactCleanupOptions(TimeSpan.FromSeconds(30)));
        Assert.NotNull(new ArtifactMaintenanceOptions(TimeSpan.FromMinutes(2)));
    }

    [Fact]
    public void Limits_reject_each_out_of_profile_resource_and_accept_smaller_profiles()
    {
        Assert.NotNull(new ArtifactLimits(1, 1, 1, 0, 1, 1, 1, 1, 1, 1));
        Action[] invalid = [
            () => _ = new ArtifactLimits(artifactBytes: 0), () => _ = new ArtifactLimits(stagingBytes: 1),
            () => _ = new ArtifactLimits(stagingBytes: long.MaxValue), () => _ = new ArtifactLimits(transferSlots: 5),
            () => _ = new ArtifactLimits(transferSlots: 0), () => _ = new ArtifactLimits(waitingCalls: 33),
            () => _ = new ArtifactLimits(copyBufferBytes: 262145), () => _ = new ArtifactLimits(transferBufferBytes: 1),
            () => _ = new ArtifactLimits(liveTickets: 100001), () => _ = new ArtifactLimits(committedIdentities: 0),
            () => _ = new ArtifactLimits(decisionBytes: 16385), () => _ = new ArtifactLimits(pageBytes: 1048577)];
        foreach (var create in invalid) { Assert.Throws<ArgumentException>(create); }
    }

    [Fact]
    public void Public_diagnostic_formatting_is_redacted_and_contract_members_are_get_only()
    {
        var stamp = new ArtifactStamp(Store(), new ArtifactIdentity(Digest, 0), Guid.NewGuid());
        ArtifactDiagnostic[] values = [
            stamp, new ArtifactCommitEvidence(stamp, Guid.NewGuid(), Guid.NewGuid(), ArtifactTestData.OpaqueCanary,
                ArtifactPublicationOutcome.Published),
            new ArtifactOption<string>.Some(ArtifactTestData.Canary), new ArtifactLimits()];
        foreach (var value in values) { ArtifactTestData.AssertSanitized(value.ToString()); }
        foreach (var type in typeof(ArtifactIdentity).Assembly.GetTypes().Where(type => type.Namespace == "Hoard.Abstractions.Storage"))
        {
            foreach (var property in type.GetProperties().Where(property => property.DeclaringType == type))
            { Assert.Null(property.SetMethod); }
        }
    }
}
