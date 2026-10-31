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
        var observed = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.MutationApplied, () =>
        {
            Interlocked.Increment(ref observed);
            throw new InvalidOperationException("Synthetic private failure " + MetadataReconciliationAssertions.CorruptionCanary);
        }, cancellationToken))
        {
            await DiagnosticsAsync(store, observeCounters, MetadataReconciliationAssertions.CorruptionCanary,
                Sanitized, cancellationToken);
        }
        Assert.Equal(1, observed);
    }

    /// <summary>Uses the caller's installed failure hook and canary; the caller retains hook ownership.</summary>
    public static async Task DiagnosticsAsync(
        IMetadataStore store, Func<MetadataFaultCounters> observeCounters, string canary,
        Action<string> assertSanitized, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeCounters);
        ArgumentException.ThrowIfNullOrEmpty(canary);
        ArgumentNullException.ThrowIfNull(assertSanitized);
        var before = observeCounters();
        var commitFailure = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutRegistry(
                Registry(), new ExpectedRevision.Absent())), new(), cancellationToken));
        Assert.Equal(MetadataFailureCode.InternalFailure, commitFailure.Code);
        CheckSanitized(commitFailure.ToString());
        Assert.Equal(before.InternalFailures + 1, observeCounters().InternalFailures);
        Assert.Equal(before.IncompleteCleanups, observeCounters().IncompleteCleanups);
        await Missing(store, Registry().Selector, cancellationToken);
        foreach (var code in Enum.GetValues<MetadataFailureCode>())
        {
            var failure = new MetadataResult<MetadataPage>.Failure(code, MetadataPhase.Commit,
                MetadataRetryDisposition.OperatorRecovery, Id(1));
            Assert.Equal(code, failure.Code);
            CheckSanitized(failure.ToString());
        }
        foreach (var value in new MetadataDiagnostic[]
        {
            new MetadataArtifactEvidence(canary),
            new MetadataContinuation(canary),
            new PublicLabel(canary),
            new MetadataSecretReference("fixture", "resolver", canary)
        })
        {
            CheckSanitized(value.ToString());
            var display = Assert.IsType<DebuggerDisplayAttribute>(
                Attribute.GetCustomAttribute(value.GetType(), typeof(DebuggerDisplayAttribute), inherit: true));
            CheckSanitized(display.Value);
        }

        void CheckSanitized(string value)
        {
            Assert.True(!value.Contains(canary, StringComparison.Ordinal),
                "Synthetic private content entered a diagnostic.");
            assertSanitized(value);
        }
    }

    private static void Sanitized(string value) =>
        Assert.True(!value.Contains(MetadataReconciliationAssertions.CorruptionCanary, StringComparison.Ordinal),
            "Synthetic private content entered a diagnostic.");
}
