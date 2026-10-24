using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Local;

public static class LocalArtifactAssertionSessions
{
    public static ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        ArtifactAssertionOwnership.CreateAsync(context, "fixture.artifact.local", ArtifactAssertionRestart.Compatible,
            (ownership, generation) => new Session(ownership, generation), cancellationToken);

    private sealed class Session : ArtifactAssertionSession
    {
        private readonly LocalArtifactStore store;
        private readonly LocalFaultControls controls = new();

        public Session(ArtifactAssertionOwnership ownership, ArtifactAssertionGeneration generation)
            : base(ownership, generation) =>
            store = new(generation.DirectoryPath, ownership.Context.Clock, controls);

        public override IArtifactStore Store => store;
        public override IArtifactEvidenceValidator Validator => store;
        public override IArtifactMaintenance Maintenance => store;
        public override IArtifactStoreLifetime Lifetime => store;
        protected override bool ProviderReady => store.Ready;
        public override Task ObserveWorkerSettlement() => store.WhenIdleForQualificationAsync();
        protected override void SetObserver(string boundary, Func<ValueTask> observer) => controls.SetObserver(boundary, observer);
        protected override void RemoveObserver(string boundary) => controls.RemoveObserver(boundary);

        protected override string Boundary(ArtifactObservationPoint point) => point switch
        {
            ArtifactObservationPoint.StagePrefix => "stage.prefix",
            ArtifactObservationPoint.StageVerified => "stage.verified",
            ArtifactObservationPoint.PublicationAdmitted => "publish.admitted",
            ArtifactObservationPoint.BeforePublicationDecision => "publish.before-decision",
            ArtifactObservationPoint.PublicationSelected => "publish.decided",
            ArtifactObservationPoint.ReceiptPersisted => "publish.receipted",
            ArtifactObservationPoint.ReadOpened => "read.opened",
            ArtifactObservationPoint.ReadCopy => "read.copy",
            ArtifactObservationPoint.DeleteRemoved => "delete.removed",
            ArtifactObservationPoint.DeleteReclaimed => "delete.reclaimed",
            ArtifactObservationPoint.CleanupCandidate => "cleanup.candidate",
            ArtifactObservationPoint.TransferQueued => "transfer.queued",
            ArtifactObservationPoint.BeforeReconciliation => "reconcile.before-resolution",
            ArtifactObservationPoint.ReconciliationVerified => "reconcile.verified",
            ArtifactObservationPoint.OperationReleased => "operation.released",
            ArtifactObservationPoint.OperationCompleted => "operation.completed",
            ArtifactObservationPoint.OperationReclaim => "operation.reclaim",
            _ => throw new ArgumentException("BindingInvalid")
        };
    }
}
