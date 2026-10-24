using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;
using Microsoft.Data.Sqlite;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataReconciliationTests
{
    [Fact]
    public async Task MP15_Corrupt_persisted_receipts_fail_reconciliation_and_replay_without_duplicate_effects()
    {
        await using var fixture = await OpenAsync();
        var (registry, _) = await Seed(fixture);
        var key = Aggregate(registry);
        var batch = Batch(await Ticket(fixture), new MetadataMutation.AddAggregateContribution(key, Delta(3)));
        var originalReceipt = Success(await fixture.Store.CommitAsync(batch, new(), default));
        var foreignTicket = await Ticket(fixture);
        if (fixture.DatabasePath is { } path)
        {
            await fixture.WhenIdleAsync();
            using var database = new SqliteConnection(new SqliteConnectionStringBuilder
            { DataSource = path, Mode = SqliteOpenMode.ReadWrite, Pooling = false, DefaultTimeout = 1 }.ToString());
            database.Open();
            using var select = database.CreateCommand();
            select.CommandText = "SELECT receipt,fingerprint,state FROM metadata_operations WHERE id=$id";
            select.Parameters.AddWithValue("$id", batch.Ticket.Id.Value.ToByteArray(bigEndian: true));
            string original;
            byte[] fingerprint;
            using (var row = select.ExecuteReader())
            {
                Assert.True(row.Read());
                original = row.GetString(0);
                fingerprint = row.GetFieldValue<byte[]>(1);
            }
            using var update = database.CreateCommand();
            update.CommandText = "UPDATE metadata_operations SET receipt=$receipt,fingerprint=$fingerprint,state=$state WHERE id=$id";
            update.Parameters.AddWithValue("$id", batch.Ticket.Id.Value.ToByteArray(bigEndian: true));
            var receiptParameter = update.Parameters.AddWithValue("$receipt", original);
            var fingerprintParameter = update.Parameters.AddWithValue("$fingerprint", fingerprint);
            var stateParameter = update.Parameters.AddWithValue("$state", 1);
            foreach (var shape in new[] { "null-target", "null-revision", "malformed-json", "missing-revisions",
                "oversized-revisions", "oversized-payload", "mismatched-ticket", "missing-receipt",
                "short-fingerprint", "missing-fingerprint", "text-fingerprint", "reserved-receipt",
                "abandoned-receipt", "fractional-state" })
            {
                var receipt = Assert.IsType<JsonObject>(JsonNode.Parse(original));
                receiptParameter.Value = original;
                fingerprintParameter.Value = fingerprint;
                stateParameter.Value = 1;
                switch (shape)
                {
                    case "null-target": receipt["Revisions"]![0]!["Target"] = null; break;
                    case "null-revision": receipt["Revisions"]![0]!["Revision"] = null; break;
                    case "missing-revisions": Assert.True(receipt.Remove("Revisions")); break;
                    case "oversized-revisions":
                        receipt["Revisions"] = new JsonArray(Enumerable.Range(1, 65)
                            .Select(_ => receipt["Revisions"]![0]!.DeepClone()).ToArray()); break;
                    case "mismatched-ticket": receipt["Ticket"] = JsonSerializer.SerializeToNode(foreignTicket); break;
                    case "short-fingerprint": fingerprintParameter.Value = new byte[31]; break;
                    case "missing-fingerprint": fingerprintParameter.Value = DBNull.Value; break;
                    case "text-fingerprint": fingerprintParameter.Value = new string('x', 32); break;
                    case "reserved-receipt": stateParameter.Value = 0; break;
                    case "abandoned-receipt": stateParameter.Value = 2; break;
                    case "fractional-state": stateParameter.Value = 1.5; break;
                }
                receiptParameter.Value = shape switch
                {
                    "malformed-json" => "{" + MetadataTestData.Canary,
                    "oversized-payload" => new string(' ', MetadataEncoding.MaximumBytes) + original,
                    "missing-receipt" => DBNull.Value,
                    _ => receipt.ToJsonString()
                };
                try
                {
                    Assert.Equal(1, update.ExecuteNonQuery());
                    var resolution = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
                        await fixture.Store.ReconcileAsync(batch.Ticket, new(), default));
                    var replay = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
                        await fixture.Store.CommitAsync(batch, new(), default));
                    AssertFailure(resolution.Code, resolution.Retry, resolution.Ticket);
                    AssertFailure(replay.Code, replay.Retry, replay.Ticket);
                    Assert.Equal(MetadataPhase.Reconcile, resolution.Phase);
                    Assert.Equal(MetadataPhase.Commit, replay.Phase);
                    MetadataTestData.AssertSanitized(resolution.ToString());
                    MetadataTestData.AssertSanitized(replay.ToString());
                    using (var row = select.ExecuteReader())
                    {
                        Assert.True(row.Read());
                        Assert.True(Equals(receiptParameter.Value, row.GetValue(0)), "Failed calls changed the stored receipt.");
                        Assert.True(row.IsDBNull(1) ? fingerprintParameter.Value is DBNull
                            : fingerprintParameter.Value is byte[] bytes ? bytes.AsSpan().SequenceEqual(row.GetFieldValue<byte[]>(1))
                            : Equals(fingerprintParameter.Value, row.GetValue(1)), "Failed calls changed the stored fingerprint.");
                        Assert.Equal(Convert.ToDouble(stateParameter.Value), row.GetDouble(2));
                    }
                    Assert.Equal(3, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(key))).Counters.Hits);
                    foreach (var diagnostic in fixture.Controls.Diagnostics) { MetadataTestData.AssertSanitized(diagnostic); }
                }
                finally
                {
                    receiptParameter.Value = original;
                    fingerprintParameter.Value = fingerprint;
                    stateParameter.Value = 1;
                    Assert.Equal(1, update.ExecuteNonQuery());
                }
                AssertOriginal(Success(await fixture.Store.CommitAsync(batch, new(), default)));
                AssertOriginal(Assert.IsType<MetadataResolution.Committed>(
                    Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default))).Receipt);
            }
        }
        AssertOriginal(Success(await fixture.Store.CommitAsync(batch, new(), default)));
        AssertOriginal(Assert.IsType<MetadataResolution.Committed>(
            Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default))).Receipt);
        Assert.Equal(3, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(key))).Counters.Hits);
        Assert.IsType<MetadataResolution.NotCommitted>(Success(await fixture.Store.ReconcileAsync(foreignTicket, new(), default)));

        void AssertFailure(MetadataFailureCode code, MetadataRetryDisposition retry,
            MetadataOption<MetadataOperationTicket> ticket)
        {
            Assert.Equal(MetadataFailureCode.CorruptState, code);
            Assert.Equal(MetadataRetryDisposition.OperatorRecovery, retry);
            Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(ticket).Value);
        }
        void AssertOriginal(MetadataCommitReceipt receipt) =>
            Assert.True(MetadataEncoding.Encode(originalReceipt).AsSpan().SequenceEqual(MetadataEncoding.Encode(receipt).AsSpan()),
                "Original-ticket replay changed the committed receipt.");
    }

    [Fact]
    public async Task MP15_Reconciliation_io_failure_preserves_the_unresolved_original_ticket()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.IoFailureAsync(fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP15_Reconciliation_without_exclusion_is_uncertain_not_a_noncommit_result()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.WriterContentionAsync(fixture.Store,
            token => CommonWriterAsync(fixture, token), token => CommonSettlementAsync(fixture, token), default);
    }

    [Fact]
    public async Task MP14_Replay_returns_original_receipt_and_changed_payload_conflicts()
    {
        await using var fixture = await OpenAsync();
        await MetadataPublicationAssertions.ReplayWithoutReacquisitionAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP15_Lost_acknowledgment_reconciles_and_abandonment_fences_execution()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.LostAcknowledgmentAndAbandonmentAsync(
            fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP16_Distinct_contributions_sum_and_uncertain_retries_do_not_duplicate()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.DistinctContributionsAsync(fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP17_Exact_ticket_expiry_and_clock_rollback_cannot_revive_a_ticket()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        await MetadataTimeAssertions.TicketExpiryAndRollbackAsync(fixture.Store, instant => clock.Set(instant.UnixMilliseconds), default);
    }
}
