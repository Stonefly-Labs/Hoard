using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;
using Microsoft.Data.Sqlite;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataFailureTests
{
    [Fact]
    public async Task MP20_Injected_storage_capacity_rolls_back_and_allows_same_ticket_retry()
    {
        await using var fixture = await OpenAsync();
        await MetadataFailureAssertions.StorageCapacityAsync(fixture.Store, cancellationToken =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            fixture.InjectStorageCapacityForTest();
            return ValueTask.CompletedTask;
        }, default);
    }

    [Fact]
    public async Task MP20_Live_ledger_capacity_is_classified_without_evicting_a_receipt()
    {
        await using var fixture = await OpenAsync();
        await MetadataFailureAssertions.LedgerCapacityAsync(fixture.Store, cancellationToken =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            return fixture.FillLedgerForTestAsync();
        }, default);
    }

    [Fact]
    public async Task MP21_Absence_succeeds_but_corruption_fails_the_complete_group()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var absent = Registry(99).Selector;
        var before = Success(await fixture.Store.ReadAsync(new([package.Selector, absent, registry.Selector]), new(), default));
        Assert.IsType<MetadataReadItem.NotFound>(before.Items[1]);
        Success(await fixture.CorruptRecordForTestAsync(registry.Selector));
        Assert.Equal(MetadataFailureCode.CorruptState, Failed(await fixture.Store.ReadAsync(new([package.Selector, absent, registry.Selector]), new(), default)));
    }

    [Fact]
    public async Task MP21_Stored_page_corruption_fails_whole_and_preserves_data()
    {
        await using var fixture = await OpenAsync();
        var damaged = Registry(2) with { Label = new(MetadataTestData.Canary) };
        await Commit(fixture, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(damaged, new ExpectedRevision.Absent()));
        var query = Registries();
        var baseline = Success(await fixture.Store.ReadPageAsync(query, new(), default));
        Assert.Equal(2, baseline.Records.Length);
        foreach (var invalid in new[] { query with { PageSize = 101 }, query with
        {
            Continuation = new MetadataOption<MetadataContinuation>.Some(new(MetadataTestData.Canary))
        } })
        {
            var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                await fixture.Store.ReadPageAsync(invalid, new(), default));
            Assert.Equal(MetadataFailureCode.InvalidInput, failure.Code);
            Assert.Equal(MetadataRetryDisposition.CorrectInput, failure.Retry);
            Assert.Equal(MetadataPhase.Page, failure.Phase);
            MetadataTestData.AssertSanitized(failure.ToString());
        }
        if (fixture.DatabasePath is { } path)
        {
            await fixture.WhenIdleAsync();
            using var database = new SqliteConnection(new SqliteConnectionStringBuilder
            { DataSource = path, Mode = SqliteOpenMode.ReadWrite, Pooling = false, DefaultTimeout = 1 }.ToString());
            database.Open();
            using var select = database.CreateCommand();
            select.CommandText = "SELECT payload FROM metadata_records WHERE key=$key";
            select.Parameters.AddWithValue("$key", MetadataEncoding.Key(damaged.Selector).ToArray());
            var original = Assert.IsType<string>(select.ExecuteScalar());
            using var update = database.CreateCommand();
            update.CommandText = "UPDATE metadata_records SET payload=$payload WHERE key=$key";
            update.Parameters.AddWithValue("$key", MetadataEncoding.Key(damaged.Selector).ToArray());
            var payload = update.Parameters.Add("$payload", SqliteType.Text);
            foreach (var shape in new[] { "null-label", "oversized-label", "null-revision", "malformed-json", "mismatched-key" })
            {
                var record = Assert.IsType<JsonObject>(JsonNode.Parse(original));
                switch (shape)
                {
                    case "null-label": record["Label"] = null; break;
                    case "oversized-label": record["Label"]!["Value"] = new string('x', 513) + MetadataTestData.Canary; break;
                    case "null-revision": record["Revision"] = null; break;
                    case "mismatched-key": record["Id"] = JsonSerializer.SerializeToNode(Id(99)); break;
                }
                var corrupt = shape == "malformed-json" ? "{" + MetadataTestData.Canary : record.ToJsonString();
                try
                {
                    payload.Value = corrupt;
                    Assert.Equal(1, update.ExecuteNonQuery());
                    var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                        await fixture.Store.ReadPageAsync(query, new(), default));
                    Assert.Equal(MetadataFailureCode.CorruptState, failure.Code);
                    Assert.Equal(MetadataRetryDisposition.OperatorRecovery, failure.Retry);
                    Assert.Equal(MetadataPhase.Page, failure.Phase);
                    MetadataTestData.AssertSanitized(failure.ToString());
                    var grouped = Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(
                        await fixture.Store.ReadAsync(new([Registry().Selector, damaged.Selector]), new(), default));
                    Assert.Equal(MetadataFailureCode.CorruptState, grouped.Code);
                    Assert.Equal(MetadataRetryDisposition.OperatorRecovery, grouped.Retry);
                    Assert.Equal(MetadataPhase.Read, grouped.Phase);
                    MetadataTestData.AssertSanitized(grouped.ToString());
                    Assert.True(corrupt == Assert.IsType<string>(select.ExecuteScalar()), "Failed reads changed stored data.");
                    foreach (var diagnostic in fixture.Controls.Diagnostics) { MetadataTestData.AssertSanitized(diagnostic); }
                }
                finally
                {
                    payload.Value = original;
                    Assert.Equal(1, update.ExecuteNonQuery());
                }
                var restored = Success(await fixture.Store.ReadPageAsync(query, new(), default));
                Assert.True(MetadataEncoding.Encode(baseline).AsSpan().SequenceEqual(MetadataEncoding.Encode(restored).AsSpan()),
                    "Restored page differs from the original committed page.");
                Assert.IsType<MetadataOption<MetadataContinuation>.None>(restored.Continuation);
                await Read<MetadataRegistry>(fixture, damaged.Selector);
            }
        }
        Success(await fixture.CorruptRecordForTestAsync(damaged.Selector));
        var corrupted = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
            await fixture.Store.ReadPageAsync(query, new(), default));
        Assert.Equal(MetadataFailureCode.CorruptState, corrupted.Code);
        Assert.Equal(MetadataRetryDisposition.OperatorRecovery, corrupted.Retry);
        Assert.Equal(MetadataPhase.Page, corrupted.Phase);
        MetadataTestData.AssertSanitized(corrupted.ToString());
    }

    [Theory]
    [InlineData("cache-auth")]
    [InlineData("aggregate-auth")]
    [InlineData("aggregate-start")]
    [InlineData("aggregate-end")]
    [InlineData("lease-resource")]
    public async Task MP21_Corrupt_query_dimensions_cannot_disappear_behind_page_filters(string shape)
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var first = Entry(package, target: "/a");
        var damaged = Entry(package, target: "/b");
        var aggregate = Aggregate(registry);
        await Commit(fixture, Publish(fixture, first), Publish(fixture, damaged),
            Publish(fixture, Entry(package, partition: "other", target: "/a0")),
            Publish(fixture, Entry(package, partition: "other", target: "/a1")),
            Publish(fixture, Entry(package, partition: "other", target: "/a2")),
            new MetadataMutation.AddAggregateContribution(aggregate, Delta()),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry, "other"), Delta()),
            new MetadataMutation.AddAggregateContribution(aggregate with { Start = new(1) }, Delta()),
            new MetadataMutation.AcquireLease(new("maintenance-a"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("maintenance-b"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("other-a"), Id(3), 300));
        MetadataPageQuery query = shape switch
        {
            "cache-auth" => new MetadataPageQuery.CacheEntries(registry.Id, new("anonymous"),
                new MetadataOption<MetadataPackageKey>.Some(package.Key))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            "lease-resource" => new MetadataPageQuery.Leases(new("maintenance-"))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            _ => new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), aggregate.Start, aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() }
        };
        MetadataSelector selector = shape switch
        {
            "cache-auth" => damaged.Selector,
            "lease-resource" => new MetadataSelector.Lease(new("maintenance-b")),
            _ => new MetadataSelector.Aggregate(aggregate)
        };
        MetadataPageQuery[] emptyQueries = [
            new MetadataPageQuery.CacheEntries(registry.Id, new("foreign"), None<MetadataPackageKey>())
                { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("foreign"), aggregate.Start, aggregate.End)
                { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), new(2), aggregate.End)
                { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Leases(new("foreign-"))
                { PageSize = 100, Continuation = None<MetadataContinuation>() }];
        var baseline = Success(await fixture.Store.ReadPageAsync(query, new(), default));
        Assert.Equal(shape.StartsWith("aggregate-", StringComparison.Ordinal) ? 1 : 2, baseline.Records.Length);
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(fixture, empty)); }
        if (fixture.DatabasePath is { } path)
        {
            await fixture.WhenIdleAsync();
            using var database = new SqliteConnection(new SqliteConnectionStringBuilder
            { DataSource = path, Mode = SqliteOpenMode.ReadWrite, Pooling = false, DefaultTimeout = 1 }.ToString());
            database.Open();
            using var select = database.CreateCommand();
            select.CommandText = "SELECT payload FROM metadata_records WHERE key=$key";
            select.Parameters.AddWithValue("$key", MetadataEncoding.Key(selector).ToArray());
            var original = Assert.IsType<string>(select.ExecuteScalar());
            var record = Assert.IsType<JsonObject>(JsonNode.Parse(original));
            switch (shape)
            {
                case "cache-auth": record["Identity"]!["AuthorizationPartition"] = null; break;
                case "aggregate-auth": record["Key"]!["AuthorizationPartition"] = null; break;
                case "aggregate-start": record["Key"]!["Start"] = null; break;
                case "aggregate-end": record["Key"]!["End"] = null; break;
                case "lease-resource": record["Resource"] = null; break;
            }
            var corrupt = record.ToJsonString();
            using var update = database.CreateCommand();
            update.CommandText = "UPDATE metadata_records SET payload=$payload WHERE key=$key";
            update.Parameters.AddWithValue("$key", MetadataEncoding.Key(selector).ToArray());
            var payload = update.Parameters.AddWithValue("$payload", corrupt);
            try
            {
                Assert.Equal(1, update.ExecuteNonQuery());
                var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                    await fixture.Store.ReadPageAsync(query, new(), default));
                Assert.Equal(MetadataFailureCode.CorruptState, failure.Code);
                Assert.Equal(MetadataRetryDisposition.OperatorRecovery, failure.Retry);
                Assert.Equal(MetadataPhase.Page, failure.Phase);
                MetadataTestData.AssertSanitized(failure.ToString());
                var grouped = Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(
                    await fixture.Store.ReadAsync(new([registry.Selector, selector]), new(), default));
                Assert.Equal(MetadataFailureCode.CorruptState, grouped.Code);
                Assert.Equal(MetadataPhase.Read, grouped.Phase);
                Assert.True(corrupt == Assert.IsType<string>(select.ExecuteScalar()), "Failed reads changed stored data.");
                foreach (var diagnostic in fixture.Controls.Diagnostics) { MetadataTestData.AssertSanitized(diagnostic); }
            }
            finally
            {
                payload.Value = original;
                Assert.Equal(1, update.ExecuteNonQuery());
            }
        }
        var restored = Success(await fixture.Store.ReadPageAsync(query, new(), default));
        Assert.True(MetadataEncoding.Encode(baseline).AsSpan().SequenceEqual(MetadataEncoding.Encode(restored).AsSpan()),
            "Restored scoped page differs from the original committed page.");
        Assert.Equal(baseline.Records.Select(record => record.Selector),
            (await Traverse(fixture, query with { PageSize = 1 })).Select(record => record.Selector));
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(fixture, empty)); }
    }

    [Fact]
    public async Task MP22_Diagnostics_and_all_failure_shapes_are_sanitized()
    {
        await using var fixture = await OpenAsync();
        fixture.Controls.SetObserver("mutation.applied", () => throw new InvalidOperationException(
            "Data Source=/private/" + MetadataTestData.Canary + ";Password=" + MetadataTestData.Canary));
        var result = await fixture.Store.CommitAsync(Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(
            Registry() with { Label = new(MetadataTestData.Canary) }, new ExpectedRevision.Absent())), new(), default);
        Assert.Equal(MetadataFailureCode.InternalFailure, Failed(result));
        foreach (var diagnostic in fixture.Controls.Diagnostics.Append(result.ToString()!))
        { MetadataTestData.AssertSanitized(diagnostic); }
        Assert.Contains("metadata.internal_failure", fixture.Controls.Diagnostics);
        foreach (var code in Enum.GetValues<MetadataFailureCode>())
        {
            var failure = new MetadataResult<MetadataPage>.Failure(code, MetadataPhase.Commit,
                MetadataRetryDisposition.OperatorRecovery, Id(1));
            Assert.Equal(code, failure.Code);
            MetadataTestData.AssertSanitized(failure.ToString());
        }
        foreach (var value in new MetadataDiagnostic[]
        {
            new MetadataArtifactEvidence(MetadataTestData.Canary), new MetadataContinuation(MetadataTestData.Canary),
            new PublicLabel(MetadataTestData.Canary), new MetadataSecretReference("fixture", "resolver", MetadataTestData.Canary)
        })
        {
            MetadataTestData.AssertSanitized(value.ToString());
            var display = Attribute.GetCustomAttribute(value.GetType(), typeof(DebuggerDisplayAttribute), inherit: true);
            Assert.NotNull(display);
            MetadataTestData.AssertSanitized(((DebuggerDisplayAttribute)display).Value);
        }
    }
}
