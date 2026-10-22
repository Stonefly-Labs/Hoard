namespace Hoard.Abstractions.Storage;

public enum ArtifactFailureCode
{
    InvalidInput, NotFound, Conflict, Denied, Unsupported, LimitExceeded, Capacity, AccessDenied,
    Unavailable, CorruptContent, CorruptState, CancelledBeforeCommit, DeadlineExceeded, Uncertain,
    ReconciliationExpired, CleanupIncomplete, Disposed, InternalFailure, IncompatibleStore
}
public enum ArtifactPhase { Admission, Reserve, Stage, Verify, Publication, Read, Reconcile, Delete, Maintenance, Cleanup }
public enum ArtifactAction { CorrectInput, Reobserve, ReconcileExactTicket, OperatorRecovery, None }
public enum ArtifactCleanupState { Released, RetainedLiveOwnership, PendingReclamation }

public abstract record ArtifactResult<T> : ArtifactDiagnostic where T : notnull
{
    private ArtifactResult() { }
    public sealed record Success : ArtifactResult<T>
    {
        public Success(T value) => Value = value ?? throw new ArgumentNullException(nameof(value));
        public T Value { get; }
    }
    public sealed record Failure : ArtifactResult<T>
    {
        public Failure(ArtifactFailureCode code, ArtifactPhase phase, ArtifactAction action, Guid correlationId,
            ArtifactOption<ArtifactOperationTicket>? ticket = null, ArtifactCleanupState cleanup = ArtifactCleanupState.Released)
        {
            Code = ArtifactValidation.Defined(code);
            Phase = ArtifactValidation.Defined(phase);
            Action = ArtifactValidation.Defined(action);
            CorrelationId = ArtifactValidation.Id(correlationId);
            Ticket = ticket ?? new ArtifactOption<ArtifactOperationTicket>.None();
            Cleanup = ArtifactValidation.Defined(cleanup);
            ArtifactValidation.Require(code != ArtifactFailureCode.Uncertain
                || Ticket is ArtifactOption<ArtifactOperationTicket>.Some);
            ArtifactValidation.Require(code != ArtifactFailureCode.CleanupIncomplete
                || cleanup == ArtifactCleanupState.RetainedLiveOwnership);
        }
        public ArtifactFailureCode Code { get; }
        public ArtifactPhase Phase { get; }
        public ArtifactAction Action { get; }
        public Guid CorrelationId { get; }
        public ArtifactOption<ArtifactOperationTicket> Ticket { get; }
        public ArtifactCleanupState Cleanup { get; }
    }
}
