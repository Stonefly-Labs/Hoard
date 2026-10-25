using System.Collections.Immutable;
using System.Runtime.CompilerServices;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;

namespace Hoard.Metadata.Tests;

internal static class MetadataCases
{
    internal sealed class OriginalObservationSequence(
        ITestOutputHelper output, string fixtureType, [CallerMemberName] string method = "")
    {
        private ConformanceOriginalObservation? previous;

        public ConformanceOriginalObservation? Observe(MetadataFixtureSession fixture, object? owner = null,
            ConformanceOriginalObservation? parent = null)
        {
            var observation = ConformanceOriginalObservationOutput.WriteIfRequested(output,
                "Hoard.Metadata.Tests." + fixtureType + "." + method, fixture.Provider, "original-instance",
                parent, previous, ("owner", owner ?? fixture), ("store", fixture.Store), ("schema", fixture.Schema),
                ("authority", fixture.Authority), ("controls", fixture.Controls));
            previous = observation;
            return observation;
        }
    }

    public static IMetadataConformanceAuthority CommonAuthority(MetadataFixtureSession fixture) =>
        new PublicationAuthority(fixture.Authority);

    public static void ObserveOriginal(ITestOutputHelper output, MetadataFixtureSession fixture,
        IMetadataConformanceAuthority authority, string fixtureType, [CallerMemberName] string method = "",
        string? shape = null) =>
        WriteOriginal(output, fixture, authority, fixtureType, method, shape);

    public static void ObserveOriginal(ITestOutputHelper output, MetadataFixtureSession fixture,
        string fixtureType, [CallerMemberName] string method = "", string? shape = null) =>
        WriteOriginal(output, fixture, fixture.Authority, fixtureType, method, shape);

    private static void WriteOriginal(ITestOutputHelper output, MetadataFixtureSession fixture,
        object authority, string fixtureType, string method, string? shape) =>
        ConformanceOriginalObservationOutput.WriteIfRequested(output,
            "Hoard.Metadata.Tests." + fixtureType + "." + method + (shape is null ? "" : $"(shape: \"{shape}\")"),
            fixture.Provider, "original-instance", ("owner", fixture), ("store", fixture.Store),
            ("schema", fixture.Schema), ("authority", authority), ("controls", fixture.Controls));

    public static MetadataFaultCounters CommonCounters(MetadataFixtureSession fixture)
    {
        var diagnostics = fixture.Controls.Diagnostics;
        return new(fixture.Controls.ActivityCount,
            diagnostics.LongCount(code => code == "metadata.internal_failure"),
            diagnostics.LongCount(code => code == "metadata.cleanup_incomplete"));
    }

    public static void CommonDiagnosticAssertions(MetadataFixtureSession fixture)
    {
        foreach (var diagnostic in fixture.Controls.Diagnostics)
        {
            MetadataTestData.AssertSanitized(diagnostic);
            Assert.DoesNotContain(MetadataReconciliationAssertions.CorruptionCanary, diagnostic);
        }
    }

    public static ValueTask<MetadataResult<MetadataId>> CommonCorruptRecordAsync(
        MetadataFixtureSession fixture, MetadataSelector selector, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return fixture.CorruptRecordForTestAsync(selector);
    }

    public static ValueTask CommonSettlementAsync(MetadataFixtureSession fixture, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return new(fixture.WhenIdleAsync().WaitAsync(cancellationToken));
    }

    public static async ValueTask<IAsyncDisposable> CommonWriterAsync(
        MetadataFixtureSession fixture, CancellationToken cancellationToken)
    {
        var writer = await fixture.HoldWriterForTestAsync(cancellationToken);
        if (cancellationToken.IsCancellationRequested)
        {
            writer.Dispose();
            cancellationToken.ThrowIfCancellationRequested();
        }
        return new WriterLease(writer);
    }

    private sealed class WriterLease(IDisposable writer) : IAsyncDisposable
    {
        private IDisposable? held = writer;
        public ValueTask DisposeAsync()
        {
            Interlocked.Exchange(ref held, null)?.Dispose();
            return ValueTask.CompletedTask;
        }
    }

    public static MetadataContinuationCorruptionControl CommonContinuationCorruption(MetadataFixtureSession fixture) =>
        (continuation, component, corruption, cancellationToken) =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!Enum.IsDefined(component)) { throw new ArgumentOutOfRangeException(nameof(component)); }
            var shape = corruption switch
            {
                MetadataContinuationCorruption.Null => "null",
                MetadataContinuationCorruption.Omitted => "omitted",
                MetadataContinuationCorruption.WrongType => "wrong-type",
                MetadataContinuationCorruption.Empty => "empty",
                MetadataContinuationCorruption.OddHex => "odd-hex",
                MetadataContinuationCorruption.InvalidHex => "invalid-hex",
                _ => throw new ArgumentOutOfRangeException(nameof(corruption))
            };
            return ValueTask.FromResult(fixture.CorruptContinuationForTest(continuation, component.ToString(), shape));
        };

    public static async ValueTask<IMetadataCorruptionScope> CommonCorruptionAsync(
        MetadataFixtureSession fixture, MetadataCorruptionRequest request, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var scope = request switch
        {
            MetadataCorruptionRequest.Record record => await fixture.CorruptRecordPayloadForTestAsync(
                record.Selector, record.Corruption switch
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
                    _ => throw new ArgumentOutOfRangeException(nameof(request))
                }, MetadataReconciliationAssertions.CorruptionCanary, cancellationToken),
            MetadataCorruptionRequest.Operation operation => await fixture.CorruptOperationPayloadForTestAsync(
                operation.Ticket, operation.Corruption switch
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
                    _ => throw new ArgumentOutOfRangeException(nameof(request))
                }, operation.ForeignTicket, MetadataReconciliationAssertions.CorruptionCanary,
                cancellationToken),
            _ => throw new ArgumentOutOfRangeException(nameof(request))
        };
        return new CorruptionScope(scope);
    }

    private sealed class CorruptionScope(MetadataFixtureCorruptionScope scope) : IMetadataCorruptionScope
    {
        public ConformanceStateFingerprint Original { get; } = new(scope.OriginalSha256);
        public async ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken) =>
            new(await scope.ObserveSha256Async(cancellationToken));
        public ValueTask DisposeAsync() => scope.DisposeAsync();
    }

    public static MetadataObservationControl CommonObservations(MetadataFixtureSession fixture) =>
        (point, observer, cancellationToken) =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (point == MetadataObservationPoint.BeforeSchemaUpgrade)
            { return ValueTask.FromResult(fixture.ObserveBeforeSchemaUpgrade(observer)); }
            if (point == MetadataObservationPoint.SchemaCandidatePrepared)
            { return ValueTask.FromResult(fixture.ObserveSchemaCandidatePrepared(observer)); }
            var boundary = point switch
            {
                MetadataObservationPoint.BeforeCommitDecision => "M0",
                MetadataObservationPoint.AfterCommitDecision => "M1",
                MetadataObservationPoint.MutationApplied => "mutation.applied",
                MetadataObservationPoint.ReadItem => "read.item",
                MetadataObservationPoint.BeforeReconciliationDecision => "reconcile.before_decision",
                _ => throw new ArgumentOutOfRangeException(nameof(point))
            };
            return ValueTask.FromResult(fixture.Controls.RegisterObserver(boundary, observer));
        };

    private sealed class PublicationAuthority(ControlledPublicationAuthority authority) : IMetadataConformanceAuthority
    {
        public int Acquisitions => authority.Acquisitions;
        public int ActiveGuards => authority.ActiveGuards;
        public MetadataArtifactEvidence Register(ArtifactDigest digest, long length) => authority.Register(digest, length);
        public void Revoke(MetadataArtifactEvidence evidence) => authority.Revoke(evidence);
        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
            MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken) =>
            authority.AcquireAsync(evidence, options, cancellationToken);
    }

    public static MetadataId Id(int value) => new(MetadataTestData.Id(value));
    public static MetadataRevision Revision() => new(Guid.NewGuid());
    public static MetadataOption<T> None<T>() where T : notnull => new MetadataOption<T>.None();
    public static T Success<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new Xunit.Sdk.XunitException($"Expected metadata success; got {failure.Code}/{failure.Phase}."),
        _ => throw new Xunit.Sdk.XunitException("Unknown metadata outcome.")
    };
    public static MetadataFailureCode Failed<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Failure>(result).Code;
    public static async ValueTask<MetadataFixtureSession> OpenAsync(MetadataTestClock? clock = null)
    {
        var fixture = MetadataFixtureSession.CreateFromEnvironment(clock ?? new());
        try
        {
            Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            return fixture;
        }
        catch { await fixture.DisposeAsync(); throw; }
    }
    public static async ValueTask<MetadataOperationTicket> Ticket(MetadataFixtureSession fixture) =>
        Success(await fixture.Store.ReserveOperationAsync(new(), default));
    public static MetadataMutationBatch Batch(MetadataOperationTicket ticket, params MetadataMutation[] mutations) =>
        new(ticket, [.. mutations], None<MetadataLeaseGuard>());
    public static async ValueTask<MetadataCommitReceipt> Commit(MetadataFixtureSession fixture, params MetadataMutation[] mutations) =>
        Success(await fixture.Store.CommitAsync(Batch(await Ticket(fixture), mutations), new(), default));
    public static async ValueTask<T> Read<T>(MetadataFixtureSession fixture, MetadataSelector key) where T : MetadataRecord =>
        Assert.IsType<T>(Assert.IsType<MetadataReadItem.Found>(
            Success(await fixture.Store.ReadAsync(new([key]), new(), default)).Items[0]).Record);
    public static async ValueTask Missing(MetadataFixtureSession fixture, MetadataSelector key) =>
        Assert.IsType<MetadataReadItem.NotFound>(Success(await fixture.Store.ReadAsync(new([key]), new(), default)).Items[0]);
    public static MetadataRegistry Registry(int value = 1) => new()
    {
        Id = Id(value),
        Ecosystem = new("nuget"),
        Upstream = new("https://packages.example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic registry"),
        PolicyId = None<MetadataId>(),
        Secret = None<MetadataSecretReference>(),
        Revision = Revision()
    };
    public static MetadataPackage Package(MetadataRegistry registry, string name = "example.package") => new()
    {
        Key = new(registry.Id, registry.Ecosystem, new(name)),
        Label = new("synthetic package"),
        Revision = Revision()
    };
    public static MetadataPolicy Policy(int value = 9) => new()
    {
        Id = Id(value),
        Scope = new MetadataPolicyScope.Global(),
        MetadataTtlMilliseconds = 31536000000,
        RetentionMilliseconds = 0,
        MaximumArtifactBytes = long.MaxValue,
        Immutable = false,
        StaleIfErrorMilliseconds = 1,
        Revision = Revision()
    };
    public static ArtifactDigest Digest(int value = 1) => new(value.ToString("x64"));
    public static MetadataCacheEntry Entry(MetadataPackage package, string partition = "anonymous", string target = "/flat/example/1.0.0") => new()
    {
        Identity = new(package.Key.RegistryId, package.Key.Ecosystem, new(target), "GET", new(partition)),
        Package = package.Key,
        Digest = Digest(),
        Length = 1024,
        Status = 200,
        Headers = new([new("etag", "\"synthetic\""), new("cache-control", "max-age=60")]),
        Created = new(0),
        Validated = new(1),
        FreshUntil = new(253402300799999),
        Revision = Revision()
    };
    public static MetadataAggregateKey Aggregate(MetadataRegistry registry, string partition = "anonymous") =>
        new(registry.Id, new(partition), new(0), new(86400000));
    public static MetadataAggregateDelta Delta(long hits = 1) => new()
    { Hits = hits, Misses = 0, BytesServed = 0, BytesFetched = 0, LatencyMilliseconds = 0, Samples = 1 };
    public static async ValueTask<(MetadataRegistry Registry, MetadataPackage Package)> Seed(MetadataFixtureSession fixture)
    {
        var registry = Registry();
        var package = Package(registry);
        await Commit(fixture, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        return (await Read<MetadataRegistry>(fixture, registry.Selector), await Read<MetadataPackage>(fixture, package.Selector));
    }
    public static MetadataMutation.PublishCacheEntry Publish(MetadataFixtureSession fixture, MetadataCacheEntry entry,
        ExpectedRevision? expected = null) =>
        new(entry, expected ?? new ExpectedRevision.Absent(), fixture.Authority.Register(entry.Digest, entry.Length));
    public static MetadataPageQuery Registries(int count = 100, MetadataOption<MetadataContinuation>? continuation = null) =>
        new MetadataPageQuery.Registries { PageSize = count, Continuation = continuation ?? None<MetadataContinuation>() };
    public static async ValueTask<ImmutableArray<MetadataRecord>> Traverse(MetadataFixtureSession fixture, MetadataPageQuery query)
    {
        var records = ImmutableArray.CreateBuilder<MetadataRecord>();
        for (var pages = 0; pages < 1000; pages++)
        {
            var page = Success(await fixture.Store.ReadPageAsync(query, new(), default));
            records.AddRange(page.Records);
            if (page.Continuation is MetadataOption<MetadataContinuation>.None) { return records.ToImmutable(); }
            query = query with { Continuation = page.Continuation };
        }
        throw new Xunit.Sdk.XunitException("Metadata traversal did not terminate.");
    }
}
