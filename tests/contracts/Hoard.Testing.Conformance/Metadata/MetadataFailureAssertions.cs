using System.Diagnostics;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataFailureAssertions
{
    public static async Task StorageCapacityAsync(
        IMetadataStore store, Func<CancellationToken, ValueTask> injectCapacityAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(injectCapacityAsync);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        await injectCapacityAsync(cancellationToken);
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await store.CommitAsync(batch, new(), cancellationToken)));
        await Missing(store, Registry().Selector, cancellationToken);
        Success(await store.CommitAsync(batch, new(), cancellationToken));
        await Read<MetadataRegistry>(store, Registry().Selector, cancellationToken);
    }

    public static async Task LedgerCapacityAsync(
        IMetadataStore store, Func<CancellationToken, ValueTask<MetadataResult<MetadataId>>> fillLedgerAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(fillLedgerAsync);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var receipt = Success(await store.CommitAsync(batch, new(), cancellationToken));
        Success(await fillLedgerAsync(cancellationToken));
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
        var stored = Assert.IsType<MetadataResolution.Committed>(
            Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
        Assert.Equal(receipt.CommitId, stored.Receipt.CommitId);
        Assert.Equal(receipt.CommitId, Success(await store.CommitAsync(batch, new(), cancellationToken)).CommitId);
    }

    public static async Task DiagnosticsAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, Func<MetadataFaultCounters> observeCounters,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(observeCounters);
        var before = observeCounters();
        var observed = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.MutationApplied, () =>
        {
            Interlocked.Increment(ref observed);
            throw new InvalidOperationException("Synthetic private failure " + MetadataReconciliationAssertions.CorruptionCanary);
        }, cancellationToken))
        {
            var failure = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await store.CommitAsync(
                Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutRegistry(
                    Registry(), new ExpectedRevision.Absent())), new(), cancellationToken));
            Assert.Equal(MetadataFailureCode.InternalFailure, failure.Code);
            Sanitized(failure.ToString());
        }
        Assert.Equal(1, observed);
        Assert.Equal(before.InternalFailures + 1, observeCounters().InternalFailures);
        Assert.Equal(before.IncompleteCleanups, observeCounters().IncompleteCleanups);
        await Missing(store, Registry().Selector, cancellationToken);
        foreach (var code in Enum.GetValues<MetadataFailureCode>())
        {
            var failure = new MetadataResult<MetadataPage>.Failure(code, MetadataPhase.Commit,
                MetadataRetryDisposition.OperatorRecovery, Id(1));
            Assert.Equal(code, failure.Code);
            Sanitized(failure.ToString());
        }
        foreach (var value in new MetadataDiagnostic[]
        {
            new MetadataArtifactEvidence(MetadataReconciliationAssertions.CorruptionCanary),
            new MetadataContinuation(MetadataReconciliationAssertions.CorruptionCanary),
            new PublicLabel(MetadataReconciliationAssertions.CorruptionCanary),
            new MetadataSecretReference("fixture", "resolver", MetadataReconciliationAssertions.CorruptionCanary)
        })
        {
            Sanitized(value.ToString());
            var display = Assert.IsType<DebuggerDisplayAttribute>(
                Attribute.GetCustomAttribute(value.GetType(), typeof(DebuggerDisplayAttribute), inherit: true));
            Sanitized(display.Value);
        }
    }

    private static void Sanitized(string value) =>
        Assert.True(!value.Contains(MetadataReconciliationAssertions.CorruptionCanary, StringComparison.Ordinal),
            "Synthetic private content entered a diagnostic.");
}
