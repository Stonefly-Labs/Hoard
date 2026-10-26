using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.ObjectSemantics;
using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;

public static class ObjectArtifactAssertionSessions
{
    public static ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, new(), cancellationToken);

    public static ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, ArtifactAssertionOptions options, CancellationToken cancellationToken) =>
        ArtifactAssertionOwnership.CreateAsync(context, "fixture.artifact.object", ArtifactAssertionRestart.FreshEpoch, options,
            (ownership, generation) => new Session(ownership, generation), cancellationToken);

    private sealed class Session : ArtifactAssertionSession
    {
        private readonly ObjectArtifactStore store;
        private readonly ObjectFaultControls controls = new();

        public Session(ArtifactAssertionOwnership ownership, ArtifactAssertionGeneration generation)
            : base(ownership, generation) =>
            store = new(generation.DirectoryPath, ownership.Context.Clock, controls);

        public override IArtifactStore Store => store;
        public override IArtifactEvidenceValidator Validator => store;
        public override IArtifactMaintenance Maintenance => store;
        public override IArtifactStoreLifetime Lifetime => store;
        protected override bool ProviderReady => store.Ready;
        public override Task ObserveWorkerSettlement() => store.WhenIdleForQualificationAsync();
        protected override ValueTask<ArtifactResult<long>> DamageProviderPayloadAsync(
            ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken) =>
            store.DamagePayloadForQualificationAsync(stamp, truncate, cancellationToken);
        protected override ValueTask<ArtifactResult<byte[]>> CaptureProviderPayloadAsync(
            ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken) =>
            store.CapturePayloadForQualificationAsync(stamp, maximumBytes, cancellationToken);
        protected override ValueTask<ArtifactResult<long>> ReplaceProviderPayloadAsync(
            ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken) =>
            store.ReplacePayloadForQualificationAsync(stamp, payload, cancellationToken);
        protected override ValueTask<ArtifactResult<long>> RemoveProviderPayloadAsync(
            ArtifactStamp stamp, CancellationToken cancellationToken) =>
            store.RemovePayloadForQualificationAsync(stamp, cancellationToken);
        protected override void SetObserver(string boundary, Func<ValueTask> observer) => controls.SetObserver(boundary, observer);
        protected override void RemoveObserver(string boundary) => controls.RemoveObserver(boundary);
        protected override void SetSynchronousStorageHold(Action? hold) => controls.BeforeObjectDelete = hold;
        protected override void SetHistoryCandidateObserver(Action<string, string>? observer) =>
            controls.BeforeHistoryCandidate = observer;

        protected override string Boundary(ArtifactObservationPoint point) => point switch
        {
            ArtifactObservationPoint.StagePrefix => "multipart.part",
            ArtifactObservationPoint.StageVerified => "multipart.complete",
            ArtifactObservationPoint.PublicationAdmitted => "object.publication-admitted",
            ArtifactObservationPoint.BeforePublicationDecision => "pointer.compare",
            ArtifactObservationPoint.PublicationSelected => "pointer.selected",
            ArtifactObservationPoint.ReceiptPersisted => "object.receipted",
            ArtifactObservationPoint.ReadOpened => "object.read-opened",
            ArtifactObservationPoint.ReadCopy => "object.read",
            ArtifactObservationPoint.DeleteRemoved => "pointer.tombstone",
            ArtifactObservationPoint.DeleteReclaimed => "object.reclaimed",
            ArtifactObservationPoint.CleanupCandidate => "multipart.cleanup",
            ArtifactObservationPoint.TransferQueued => "object.transfer-queued",
            ArtifactObservationPoint.BeforeReconciliation => "object.reconcile-before-resolution",
            ArtifactObservationPoint.ReconciliationVerified => "object.reconcile-verified",
            ArtifactObservationPoint.OperationReleased => "object.operation-released",
            ArtifactObservationPoint.OperationCompleted => "object.operation-completed",
            ArtifactObservationPoint.OperationReclaim => "object.operation-reclaim",
            ArtifactObservationPoint.PayloadDamage => "object.payload-damage",
            ArtifactObservationPoint.DirectVerification => "object.direct",
            ArtifactObservationPoint.CommitProgress => "object.commit-progress",
            ArtifactObservationPoint.PayloadSelected => "object.qualification-payload-selected",
            _ => throw new ArgumentException("BindingInvalid")
        };
    }
}
