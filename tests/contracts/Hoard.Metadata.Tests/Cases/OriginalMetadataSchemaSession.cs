using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

internal sealed class OriginalMetadataSchemaSession(MetadataFixtureSession fixture) : IMetadataSchemaAssertionSession
{
    public IMetadataStore Store => fixture.Store;
    public IMetadataSchemaAdministration Schema => fixture.Schema;
    public IMetadataConformanceAuthority Authority => CommonAuthority(fixture);
    public async ValueTask<IMetadataSchemaAssertionSession> ReopenAsync(CancellationToken cancellationToken) =>
        new OriginalMetadataSchemaSession(await fixture.ReopenAsync("fixture-sqlite-v2", cancellationToken));
    public async ValueTask<ConformanceStateFingerprint> ObserveStateAsync(CancellationToken cancellationToken) =>
        new(await fixture.ObserveSchemaStateForTestAsync(cancellationToken));
    public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutAsync(bool partial, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return fixture.CreateUnrecognizedLayoutForTestAsync(partial);
    }
    public ValueTask<MetadataResult<MetadataId>> SetFutureSchemaAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return fixture.MakeFutureSchemaForTestAsync();
    }
    public ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(MetadataSelector selector, CancellationToken cancellationToken) =>
        CommonCorruptRecordAsync(fixture, selector, cancellationToken);
    public ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync(CancellationToken cancellationToken) =>
        fixture.AuthorizeUpgradeAsync(cancellationToken);
    public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        MetadataObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken) =>
        CommonObservations(fixture)(point, observer, cancellationToken);
    public ValueTask AwaitSettlementAsync(CancellationToken cancellationToken) =>
        CommonSettlementAsync(fixture, cancellationToken);
    public ValueTask DisposeAsync() => fixture.DisposeAsync();
}
