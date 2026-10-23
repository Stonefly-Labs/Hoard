using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;

namespace Hoard.Conformance.Tests;

public sealed class MemoryMechanismTests
{
    [Fact]
    public async Task Targeted_record_damage_fails_group_and_page_without_changing_the_damage()
    {
        await using var store = await OpenAsync();
        var registry = Registry(1);
        var healthy = Registry(2);
        await Commit(store, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(healthy, new ExpectedRevision.Absent()));
        var original = Success(await store.RecordPayloadForTestAsync(registry.Selector));
        var query = new MetadataPageQuery.Registries { PageSize = 100, Continuation = new MetadataOption<MetadataContinuation>.None() };
        var baseline = Success(await store.ReadPageAsync(query, new(), default));
        foreach (var shape in new[] { "null-label", "oversized-label", "null-revision", "malformed", "wrong-key" })
        {
            var record = Assert.IsType<JsonObject>(JsonNode.Parse(original));
            switch (shape)
            {
                case "null-label": record["Label"] = null; break;
                case "oversized-label": record["Label"]!["Value"] = new string('x', 513); break;
                case "null-revision": record["Revision"] = null; break;
                case "wrong-key": record["Id"] = JsonSerializer.SerializeToNode(new MetadataId(Guid.NewGuid())); break;
            }
            var damaged = shape == "malformed" ? "{" : record.ToJsonString();
            Success(await store.ReplaceRecordPayloadForTestAsync(registry.Selector, damaged));
            try
            {
                var page = Assert.IsType<MetadataResult<MetadataPage>.Failure>(await store.ReadPageAsync(query, new(), default));
                var group = Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(
                    await store.ReadAsync(new([healthy.Selector, registry.Selector]), new(), default));
                Assert.Equal(MetadataFailureCode.CorruptState, page.Code);
                Assert.Equal(MetadataFailureCode.CorruptState, group.Code);
                Assert.Equal(MetadataRetryDisposition.OperatorRecovery, page.Retry);
                Assert.Equal(MetadataRetryDisposition.OperatorRecovery, group.Retry);
                Assert.Equal(damaged, Success(await store.RecordPayloadForTestAsync(registry.Selector)));
                var unaffected = Success(await store.ReadAsync(new([healthy.Selector]), new(), default));
                Assert.IsType<MetadataReadItem.Found>(Assert.Single(unaffected.Items));
            }
            finally { Success(await store.ReplaceRecordPayloadForTestAsync(registry.Selector, original)); }
            Assert.Equal<byte>(MetadataEncoding.Encode(baseline), MetadataEncoding.Encode(Success(await store.ReadPageAsync(query, new(), default))));
        }
    }

    [Fact]
    public async Task Targeted_receipt_damage_preserves_original_ticket_and_independent_effects()
    {
        await using var store = await OpenAsync();
        var registry = Registry(1);
        await Commit(store, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var key = new MetadataAggregateKey(registry.Id, new("anonymous"), new(0), new(86400000));
        var ticket = Success(await store.ReserveOperationAsync(new(), default));
        var foreign = Success(await store.ReserveOperationAsync(new(), default));
        var delta = new MetadataAggregateDelta { Hits = 3, Misses = 0, BytesServed = 0, BytesFetched = 0, LatencyMilliseconds = 0, Samples = 1 };
        var batch = new MetadataMutationBatch(ticket, [new MetadataMutation.AddAggregateContribution(key, delta)], new MetadataOption<MetadataLeaseGuard>.None());
        var receipt = Success(await store.CommitAsync(batch, new(), default));
        var original = Success(await store.OperationImageForTestAsync(ticket));
        foreach (var shape in new[] { "null-target", "null-revision", "malformed", "missing-revisions",
            "oversized-revisions", "oversized-payload", "mismatched-ticket", "missing-receipt",
            "short-fingerprint", "missing-fingerprint", "invalid-fingerprint", "reserved-receipt",
            "abandoned-receipt", "fractional-state" })
        {
            var payload = Assert.IsType<JsonObject>(JsonNode.Parse(Assert.IsType<string>(original.Receipt)));
            var damaged = original;
            switch (shape)
            {
                case "null-target": payload["Revisions"]![0]!["Target"] = null; break;
                case "null-revision": payload["Revisions"]![0]!["Revision"] = null; break;
                case "missing-revisions": Assert.True(payload.Remove("Revisions")); break;
                case "oversized-revisions":
                    payload["Revisions"] = new JsonArray(Enumerable.Range(0, 65).Select(_ => payload["Revisions"]![0]!.DeepClone()).ToArray()); break;
                case "mismatched-ticket": payload["Ticket"] = JsonSerializer.SerializeToNode(foreign); break;
                case "short-fingerprint": damaged = damaged with { Fingerprint = new string('a', 62) }; break;
                case "missing-fingerprint": damaged = damaged with { Fingerprint = null }; break;
                case "invalid-fingerprint": damaged = damaged with { Fingerprint = new string('z', 64) }; break;
                case "reserved-receipt": damaged = damaged with { State = 0 }; break;
                case "abandoned-receipt": damaged = damaged with { State = 2 }; break;
                case "fractional-state": damaged = damaged with { State = 1.5 }; break;
            }
            damaged = damaged with
            {
                Receipt = shape switch
                {
                    "malformed" => "{",
                    "oversized-payload" => new string(' ', MetadataEncoding.MaximumBytes) + original.Receipt,
                    "missing-receipt" => null,
                    _ => payload.ToJsonString()
                }
            };
            Success(await store.ReplaceOperationImageForTestAsync(ticket, damaged));
            try
            {
                var reconcile = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(await store.ReconcileAsync(ticket, new(), default));
                var replay = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await store.CommitAsync(batch, new(), default));
                Assert.Equal(MetadataFailureCode.CorruptState, reconcile.Code);
                Assert.Equal(MetadataFailureCode.CorruptState, replay.Code);
                Assert.Equal(MetadataRetryDisposition.OperatorRecovery, reconcile.Retry);
                Assert.Equal(MetadataRetryDisposition.OperatorRecovery, replay.Retry);
                Assert.Equal(ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(reconcile.Ticket).Value);
                Assert.Equal(ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(replay.Ticket).Value);
                Assert.Equal(damaged, Success(await store.OperationImageForTestAsync(ticket)));
                var snapshot = Success(await store.ReadAsync(new([new MetadataSelector.Aggregate(key)]), new(), default));
                Assert.Equal(3, Assert.IsType<MetadataAccessAggregate>(Assert.IsType<MetadataReadItem.Found>(Assert.Single(snapshot.Items)).Record).Counters.Hits);
            }
            finally { Success(await store.ReplaceOperationImageForTestAsync(ticket, original)); }
            Assert.Equal<byte>(MetadataEncoding.Encode(receipt), MetadataEncoding.Encode(Success(await store.CommitAsync(batch, new(), default))));
        }
    }

    private static async Task<MemoryMetadataStore> OpenAsync()
    {
        var store = new MemoryMetadataStore(new UnusedAuthority(), TimeProvider.System, _ => ValueTask.CompletedTask,
            _ => throw new Xunit.Sdk.XunitException("Unexpected provider diagnostic."));
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        return store;
    }

    private static MetadataRegistry Registry(int value) => new()
    {
        Id = new(new Guid(value, 0, 0, new byte[8])),
        Ecosystem = new("nuget"),
        Upstream = new("https://example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic"),
        PolicyId = new MetadataOption<MetadataId>.None(),
        Secret = new MetadataOption<MetadataSecretReference>.None(),
        Revision = new(Guid.NewGuid())
    };

    private static T Success<T>(MetadataResult<T> result) where T : notnull => Assert.IsType<MetadataResult<T>.Success>(result).Value;

    private static async Task Commit(MemoryMetadataStore store, params MetadataMutation[] mutations)
    {
        var ticket = Success(await store.ReserveOperationAsync(new(), default));
        Success(await store.CommitAsync(new(ticket, [.. mutations], new MetadataOption<MetadataLeaseGuard>.None()), new(), default));
    }

    private sealed class UnusedAuthority : IMetadataPublicationAuthority
    {
        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
            MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken) =>
            throw new Xunit.Sdk.XunitException("Unexpected publication authority invocation.");
    }
}
