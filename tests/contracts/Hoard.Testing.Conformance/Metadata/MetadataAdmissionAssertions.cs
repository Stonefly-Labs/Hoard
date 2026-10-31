using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataAdmissionAssertions
{
    public static async Task ExplicitAdmissionAsync(
        IMetadataStore store, IMetadataSchemaAdministration schema, Func<MetadataFaultCounters> observeCounters,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeCounters);
        Assert.Equal(0, observeCounters().BoundaryObservations);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
        Assert.Equal(MetadataSchemaState.Empty, Success(await schema.InspectAsync(new(), cancellationToken)).State);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await schema.PrepareAsync(
            new MetadataSchemaRequest.InspectOnly(), new(), cancellationToken));
        Success(await schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        await Ticket(store, cancellationToken);
    }

    public static async Task InvalidBudgetsAsync(
        IMetadataStore store, IMetadataSchemaAdministration schema, Func<MetadataFaultCounters> observeCounters,
        Func<ValueTask> disposeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeCounters);
        ArgumentNullException.ThrowIfNull(disposeAsync);
        try
        {
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await schema.InspectAsync(new(TimeSpan.Zero), cancellationToken)));
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await schema.InspectAsync(
                new(TimeSpan.FromMinutes(3)), cancellationToken)));
            Assert.Equal(0, observeCounters().BoundaryObservations);
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReserveOperationAsync(
                new(TimeSpan.FromSeconds(31)), cancellationToken)));
            Assert.Equal(0, observeCounters().BoundaryObservations);
        }
        finally { await disposeAsync(); }
        Assert.Equal(MetadataFailureCode.Disposed, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
    }
}
