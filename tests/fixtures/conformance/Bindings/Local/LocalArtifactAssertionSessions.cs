using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Local;

public static class LocalArtifactAssertionSessions
{
    public static ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, new(), cancellationToken);

    public static ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, ArtifactAssertionOptions options, CancellationToken cancellationToken) =>
        ArtifactAssertionOwnership.CreateAsync(context, "fixture.artifact.local", ArtifactAssertionRestart.Compatible, options,
            (ownership, generation) => new Session(ownership, generation, options.AdmissionProbe), cancellationToken);

    private sealed class Session : ArtifactAssertionSession
    {
        private readonly LocalArtifactStore store;
        private readonly LocalFaultControls controls = new();

        public Session(ArtifactAssertionOwnership ownership, ArtifactAssertionGeneration generation,
            ArtifactAdmissionProbe admissionProbe) : base(ownership, generation)
        {
            controls.CapabilitiesForAdmission = value => ArtifactAdmissionCapabilities.Apply(value, admissionProbe);
            store = new(generation.DirectoryPath, ownership.Context.Clock, controls);
        }

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
        protected override ValueTask<ArtifactResult<IAsyncDisposable>> RestrictProviderPayloadAccessAsync(
            ArtifactStamp stamp, bool unavailable, Action<IAsyncDisposable> ownScope, CancellationToken cancellationToken) =>
            store.RestrictPayloadAccessForQualificationAsync(stamp, unavailable, ownScope, cancellationToken);
        protected override void SetObserver(string boundary, Func<ValueTask> observer) => controls.SetObserver(boundary, observer);
        protected override void RemoveObserver(string boundary) => controls.RemoveObserver(boundary);
        protected override void SetSynchronousStorageHold(Action? hold) => controls.BeforeRecordWrite = hold;
        protected override void SetRecordWriteFailure(Action? failure) => controls.BeforeRecordWrite = failure;
        protected override void SetHistoryCandidateObserver(Action<string, string>? observer) =>
            controls.BeforeHistoryCandidate = observer;

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
            ArtifactObservationPoint.PayloadDamage => "payload.damage",
            ArtifactObservationPoint.DirectVerification => "publish.direct",
            ArtifactObservationPoint.CommitProgress => "publish.progress",
            ArtifactObservationPoint.PayloadSelected => "qualification.payload-selected",
            _ => throw new ArgumentException("BindingInvalid")
        };
    }
}
