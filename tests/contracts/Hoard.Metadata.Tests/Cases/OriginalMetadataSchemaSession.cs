using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

internal sealed class OriginalMetadataSchemaSession : IMetadataSchemaAssertionSession
{
    private readonly MetadataFixtureSession fixture;
    private readonly OriginalObservationSequence? observations;
    private readonly ConformanceOriginalObservation? observation;

    public OriginalMetadataSchemaSession(MetadataFixtureSession fixture, OriginalObservationSequence? observations = null,
        ConformanceOriginalObservation? parent = null)
    {
        this.fixture = fixture;
        this.observations = observations;
        observation = observations?.Observe(fixture, this, parent);
    }

    public IMetadataStore Store => fixture.Store;
    public IMetadataSchemaAdministration Schema => fixture.Schema;
    public IMetadataConformanceAuthority Authority => CommonAuthority(fixture);
    public async ValueTask<IMetadataSchemaAssertionSession> ReopenAsync(CancellationToken cancellationToken)
    {
        var reopened = await fixture.ReopenAsync("fixture-sqlite-v2", cancellationToken);
        try { return new OriginalMetadataSchemaSession(reopened, observations, observation); }
        catch
        {
            await reopened.DisposeAsync();
            throw;
        }
    }
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
