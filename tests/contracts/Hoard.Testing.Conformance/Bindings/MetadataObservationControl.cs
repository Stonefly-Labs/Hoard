namespace Hoard.Testing.Conformance.Bindings;

public enum MetadataObservationPoint
{
    BeforeCommitDecision, AfterCommitDecision, MutationApplied, ReadItem, BeforeReconciliationDecision,
    BeforeSchemaUpgrade, SchemaCandidatePrepared, CorruptionCaptured, PayloadChanged
}

public delegate ValueTask<IAsyncDisposable> MetadataObservationControl(
    MetadataObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken);
