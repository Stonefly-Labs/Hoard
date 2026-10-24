using System.Collections.Concurrent;
using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Conformance.Tests;

public sealed class MemoryMechanismTests
{
    [Fact]
    public async Task Noop_corruption_fails_the_common_assertion_and_real_memory_damage_passes_unchanged()
    {
        Func<IMetadataStore, Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>>,
            CancellationToken, Task> check = MetadataReconciliationAssertions.CorruptReceiptsAsync;
        await using var undamaged = await OpenAsync();
        var failure = await Assert.ThrowsAsync<Xunit.Sdk.NotEqualException>(
            () => check(undamaged, (_, token) =>
            {
                token.ThrowIfCancellationRequested();
                return ValueTask.FromResult<IMetadataCorruptionScope>(new UnchangedCorruptionScope());
            }, default));
        Assert.Contains(nameof(MetadataReconciliationAssertions.CorruptReceiptsAsync), failure.StackTrace);
        await using var corrected = await OpenAsync();
        var control = new MemoryCorruptionControl(corrected);
        await check(corrected, control.CorruptAsync, default);
    }

    [Fact]
    public async Task Compiled_receipt_corruption_consumer_preserves_all_shapes_and_original_ticket_classification()
    {
        await using var store = await OpenAsync();
        var control = new MemoryCorruptionControl(store);
        await MetadataReconciliationAssertions.CorruptReceiptsAsync(store, control.CorruptAsync, default);
    }

    [Fact]
    public async Task Compiled_page_corruption_consumer_preserves_complete_failures_and_restoration()
    {
        await using var store = await OpenAsync();
        var control = new MemoryCorruptionControl(store);
        await MetadataCorruptionAssertions.PageRecordsAsync(store, control.CorruptAsync, control.CorruptRecordAsync, default);
    }

    [Fact]
    public async Task Compiled_absence_consumer_distinguishes_missing_records_from_corrupt_groups()
    {
        await using var store = await OpenAsync();
        var control = new MemoryCorruptionControl(store);
        await MetadataCorruptionAssertions.AbsenceAndCorruptGroupsAsync(store, control.CorruptRecordAsync, default);
    }

    [Theory]
    [InlineData(MetadataRecordCorruption.CacheAuthorization)]
    [InlineData(MetadataRecordCorruption.AggregateAuthorization)]
    [InlineData(MetadataRecordCorruption.AggregateStart)]
    [InlineData(MetadataRecordCorruption.AggregateEnd)]
    [InlineData(MetadataRecordCorruption.LeaseResource)]
    public async Task Compiled_query_dimension_consumer_rejects_corruption_before_filtering(MetadataRecordCorruption corruption)
    {
        var authority = new RegisteredAuthority();
        await using var store = await OpenAsync(authority);
        var control = new MemoryCorruptionControl(store);
        await MetadataCorruptionAssertions.QueryDimensionsAsync(store, authority, control.CorruptAsync, corruption, default);
    }

    [Fact]
    public async Task Partition_aliasing_fails_the_common_assertion_and_correct_memory_passes_unchanged()
    {
        Func<IMetadataStore, IMetadataConformanceAuthority, CancellationToken, Task> check =
            MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync;
        var faultyAuthority = new RegisteredAuthority();
        await using var faultyStore = await OpenAsync(faultyAuthority);
        var failure = await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(
            () => check(new PartitionAliasingStore(faultyStore), faultyAuthority, default));
        Assert.Contains(nameof(MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync), failure.StackTrace);
        var correctedAuthority = new RegisteredAuthority();
        await using var correctedStore = await OpenAsync(correctedAuthority);
        await check(correctedStore, correctedAuthority, default);
    }

    [Theory]
    [InlineData("ticket-expiry")]
    [InlineData("lease-rollback")]
    public async Task Compiled_time_consumers_retain_exact_expiry_and_rollback_fences(string consumer)
    {
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        await using var store = await OpenAsync(clock: clock);
        await (consumer switch
        {
            "ticket-expiry" => MetadataTimeAssertions.TicketExpiryAndRollbackAsync(store, clock, default),
            "lease-rollback" => MetadataTimeAssertions.LeaseRollbackAsync(store, clock, default),
            _ => throw new ArgumentException("Unknown common consumer.")
        });
    }

    [Fact]
    public async Task Compiled_cursor_consumer_checks_scope_size_foreign_epoch_and_live_resume()
    {
        await using var store = await OpenAsync();
        await using var foreign = await OpenAsync();
        await MetadataPagingAssertions.ContinuationScopeAndEpochAsync(store, foreign, default);
    }

    [Fact]
    public async Task Compiled_canonical_identity_consumer_preserves_text_and_rejects_forbidden_values()
    {
        await using var store = await OpenAsync();
        await MetadataIdentityAssertions.CanonicalTextAndForbiddenValuesAsync(store, default);
    }

    [Theory]
    [InlineData("competing-creates")]
    [InlineData("revision-races")]
    [InlineData("exact-bounds")]
    [InlineData("scopes-and-intervals")]
    [InlineData("bounded-pages")]
    [InlineData("lease-fences")]
    public async Task Compiled_common_consumers_execute_against_the_independent_memory_store(string consumer)
    {
        await using var store = await OpenAsync();
        await (consumer switch
        {
            "competing-creates" => MetadataConcurrencyAssertions.CompetingCreatesAsync(store, default),
            "revision-races" => MetadataConcurrencyAssertions.RevisionRacesAsync(store, default),
            "exact-bounds" => MetadataBoundsAssertions.ExactBoundsAsync(store, default),
            "scopes-and-intervals" => MetadataBoundsAssertions.ScopesAndIntervalsAsync(store, default),
            "bounded-pages" => MetadataPagingAssertions.BoundedDatasetsAsync(store, default),
            "lease-fences" => MetadataLeaseAssertions.OwnerGenerationAndRevisionFencesAsync(store, default),
            _ => throw new ArgumentException("Unknown common consumer.")
        });
    }

    [Theory]
    [InlineData("registry-isolation")]
    [InlineData("authorization-isolation")]
    [InlineData("entity-round-trips")]
    [InlineData("final-graph")]
    [InlineData("reference-replacement")]
    [InlineData("reference-aba")]
    [InlineData("telemetry-rollback")]
    [InlineData("all-page-queries")]
    [InlineData("oversized-pages")]
    public async Task Compiled_publication_consumers_corroborate_actual_memory_records_and_references(string consumer)
    {
        var authority = new RegisteredAuthority();
        await using var store = await OpenAsync(authority);
        await (consumer switch
        {
            "registry-isolation" => MetadataIdentityAssertions.RegistryIsolationAsync(store, authority, default),
            "authorization-isolation" => MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync(store, authority, default),
            "entity-round-trips" => MetadataEntityAssertions.RoundTripAndInvalidRelationshipsAsync(store, authority, default),
            "final-graph" => MetadataEntityAssertions.FinalGraphDeletionAndDisabledRetentionAsync(store, authority, default),
            "reference-replacement" => MetadataReferenceAssertions.EntryReplacementAndRemovalAsync(store, authority, default),
            "reference-aba" => MetadataReferenceAssertions.ZeroReferenceAbaFencingAsync(store, authority, default),
            "telemetry-rollback" => MetadataReferenceAssertions.InvalidTelemetryRollsBackEntryAndReferencesAsync(store, authority, default),
            "all-page-queries" => MetadataPagingAssertions.AllQueryKindsAsync(store, authority, default),
            "oversized-pages" => MetadataPagingAssertions.OversizedRequestsAndResultsAsync(store, authority, default),
            _ => throw new ArgumentException("Unknown common consumer.")
        });
    }

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
            var damaged = DamageRecord(original, shape);
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
            var damaged = DamageOperation(original, shape, foreign);
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

    private static MemoryOperationTestImage DamageOperation(
        MemoryOperationTestImage original, string shape, MetadataOperationTicket foreign)
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
            case "malformed" or "oversized-payload" or "missing-receipt": break;
            default: throw new ArgumentException("BindingInvalid");
        }
        return damaged with
        {
            Receipt = shape switch
            {
                "malformed" => "{" + MetadataReconciliationAssertions.CorruptionCanary,
                "oversized-payload" => new string(' ', MetadataEncoding.MaximumBytes) + original.Receipt,
                "missing-receipt" => null,
                _ => payload.ToJsonString()
            }
        };
    }

    private static string DamageRecord(string original, string shape)
    {
        var record = Assert.IsType<JsonObject>(JsonNode.Parse(original));
        switch (shape)
        {
            case "null-label": record["Label"] = null; break;
            case "oversized-label":
                record["Label"]!["Value"] = new string('x', 513) + MetadataReconciliationAssertions.CorruptionCanary; break;
            case "null-revision": record["Revision"] = null; break;
            case "wrong-key": record["Id"] = JsonSerializer.SerializeToNode(new MetadataId(Guid.NewGuid())); break;
            case "cache-auth": record["Identity"]!["AuthorizationPartition"] = null; break;
            case "aggregate-auth": record["Key"]!["AuthorizationPartition"] = null; break;
            case "aggregate-start": record["Key"]!["Start"] = null; break;
            case "aggregate-end": record["Key"]!["End"] = null; break;
            case "lease-resource": record["Resource"] = null; break;
            case "malformed": break;
            default: throw new ArgumentException("BindingInvalid");
        }
        return shape == "malformed" ? "{" + MetadataReconciliationAssertions.CorruptionCanary : record.ToJsonString();
    }

    private sealed class MemoryCorruptionControl(MemoryMetadataStore store)
    {
        public ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(
            MetadataSelector selector, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return store.CorruptRecordForTestAsync(selector);
        }

        public async ValueTask<IMetadataCorruptionScope> CorruptAsync(
            MetadataCorruptionRequest request, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (request is MetadataCorruptionRequest.Record record)
            {
                var originalRecord = Success(await store.RecordPayloadForTestAsync(record.Selector));
                var recordScope = new RecordScope(store, record.Selector, originalRecord);
                var recordShape = record.Corruption switch
                {
                    MetadataRecordCorruption.NullLabel => "null-label",
                    MetadataRecordCorruption.OversizedLabel => "oversized-label",
                    MetadataRecordCorruption.NullRevision => "null-revision",
                    MetadataRecordCorruption.MalformedEncoding => "malformed",
                    MetadataRecordCorruption.MismatchedKey => "wrong-key",
                    MetadataRecordCorruption.CacheAuthorization => "cache-auth",
                    MetadataRecordCorruption.AggregateAuthorization => "aggregate-auth",
                    MetadataRecordCorruption.AggregateStart => "aggregate-start",
                    MetadataRecordCorruption.AggregateEnd => "aggregate-end",
                    MetadataRecordCorruption.LeaseResource => "lease-resource",
                    _ => throw new ArgumentException("BindingInvalid")
                };
                var damagedRecord = DamageRecord(originalRecord, recordShape);
                cancellationToken.ThrowIfCancellationRequested();
                Success(await store.ReplaceRecordPayloadForTestAsync(record.Selector, damagedRecord));
                return recordScope;
            }
            var operation = request as MetadataCorruptionRequest.Operation ?? throw new ArgumentException("BindingInvalid");
            var original = Success(await store.OperationImageForTestAsync(operation.Ticket));
            var scope = new ReceiptScope(store, operation.Ticket, original);
            var shape = operation.Corruption switch
            {
                MetadataOperationCorruption.NullTarget => "null-target",
                MetadataOperationCorruption.NullRevision => "null-revision",
                MetadataOperationCorruption.MalformedEncoding => "malformed",
                MetadataOperationCorruption.MissingRevisions => "missing-revisions",
                MetadataOperationCorruption.OversizedRevisions => "oversized-revisions",
                MetadataOperationCorruption.OversizedEncoding => "oversized-payload",
                MetadataOperationCorruption.MismatchedTicket => "mismatched-ticket",
                MetadataOperationCorruption.MissingReceipt => "missing-receipt",
                MetadataOperationCorruption.ShortFingerprint => "short-fingerprint",
                MetadataOperationCorruption.MissingFingerprint => "missing-fingerprint",
                MetadataOperationCorruption.InvalidFingerprintEncoding => "invalid-fingerprint",
                MetadataOperationCorruption.ReservedReceipt => "reserved-receipt",
                MetadataOperationCorruption.AbandonedReceipt => "abandoned-receipt",
                MetadataOperationCorruption.InvalidState => "fractional-state",
                _ => throw new ArgumentException("BindingInvalid")
            };
            var damaged = DamageOperation(original, shape, operation.ForeignTicket);
            cancellationToken.ThrowIfCancellationRequested();
            Success(await store.ReplaceOperationImageForTestAsync(operation.Ticket, damaged));
            return scope;
        }

        private sealed class RecordScope(
            MemoryMetadataStore store, MetadataSelector selector, string original) : IMetadataCorruptionScope
        {
            private bool restored;
            public ConformanceStateFingerprint Original { get; } = Fingerprint(original);
            public async ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken)
            {
                cancellationToken.ThrowIfCancellationRequested();
                return Fingerprint(Success(await store.RecordPayloadForTestAsync(selector)));
            }
            public async ValueTask DisposeAsync()
            {
                if (restored) { return; }
                Success(await store.ReplaceRecordPayloadForTestAsync(selector, original));
                restored = true;
            }
            private static ConformanceStateFingerprint Fingerprint(string payload) =>
                new(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(payload))));
        }

        private sealed class ReceiptScope(
            MemoryMetadataStore store, MetadataOperationTicket ticket, MemoryOperationTestImage original) : IMetadataCorruptionScope
        {
            private bool restored;
            public ConformanceStateFingerprint Original { get; } = Fingerprint(original);
            public async ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken)
            {
                cancellationToken.ThrowIfCancellationRequested();
                return Fingerprint(Success(await store.OperationImageForTestAsync(ticket)));
            }
            public async ValueTask DisposeAsync()
            {
                if (restored) { return; }
                Success(await store.ReplaceOperationImageForTestAsync(ticket, original));
                restored = true;
            }
            private static ConformanceStateFingerprint Fingerprint(MemoryOperationTestImage image) =>
                new(Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(image))));
        }
    }

    private sealed class UnchangedCorruptionScope : IMetadataCorruptionScope
    {
        public ConformanceStateFingerprint Original { get; } = new(new string('a', 64));
        public ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return ValueTask.FromResult(Original);
        }
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }

    private static async Task<MemoryMetadataStore> OpenAsync(
        IMetadataPublicationAuthority? authority = null, TimeProvider? clock = null)
    {
        var store = new MemoryMetadataStore(authority ?? new UnusedAuthority(), clock ?? TimeProvider.System, _ => ValueTask.CompletedTask,
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

    private sealed class RegisteredAuthority : IMetadataConformanceAuthority
    {
        private readonly ConcurrentDictionary<string, MetadataCommittedArtifact> artifacts = new(StringComparer.Ordinal);

        public MetadataArtifactEvidence Register(ArtifactDigest digest, long length)
        {
            var evidence = new MetadataArtifactEvidence(Guid.NewGuid().ToString("N"));
            Assert.True(artifacts.TryAdd(evidence.Value, new(digest, length)));
            return evidence;
        }

        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
            MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return ValueTask.FromResult<MetadataResult<IMetadataPublicationGuard>>(
                artifacts.TryGetValue(evidence.Value, out var artifact)
                    ? new MetadataResult<IMetadataPublicationGuard>.Success(new Guard(artifact))
                    : new MetadataResult<IMetadataPublicationGuard>.Failure(MetadataFailureCode.InvalidInput,
                        MetadataPhase.Publication, MetadataRetryDisposition.CorrectInput, new(Guid.NewGuid())));
        }

        private sealed class Guard(MetadataCommittedArtifact artifact) : IMetadataPublicationGuard
        {
            public MetadataCommittedArtifact Artifact { get; } = artifact;
            public ValueTask DisposeAsync() => ValueTask.CompletedTask;
        }
    }

    private sealed class PartitionAliasingStore(IMetadataStore store) : IMetadataStore
    {
        public async ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
            MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken)
        {
            var result = await store.ReadAsync(request, options, cancellationToken);
            return result is MetadataResult<MetadataReadSnapshot>.Success success
                ? new MetadataResult<MetadataReadSnapshot>.Success(new(success.Value.Items.Select(item =>
                    item is MetadataReadItem.Found { Record: MetadataCacheEntry entry }
                        && entry.Identity.AuthorizationPartition.Value == "subject-opaque"
                        ? (MetadataReadItem)new MetadataReadItem.Found(entry with { Digest = new(1.ToString("x64")) })
                        : item).ToImmutableArray()))
                : result;
        }

        public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
            MetadataCallOptions options, CancellationToken cancellationToken) =>
            store.ReserveOperationAsync(options, cancellationToken);
        public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
            MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken) =>
            store.ReadPageAsync(request, options, cancellationToken);
        public ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
            MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken) =>
            store.CommitAsync(request, options, cancellationToken);
        public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
            MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken) =>
            store.ReconcileAsync(ticket, options, cancellationToken);
        public ValueTask DisposeAsync() => store.DisposeAsync();
    }
}
