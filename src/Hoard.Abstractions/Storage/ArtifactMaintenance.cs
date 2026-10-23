using System.Collections.Immutable;

namespace Hoard.Abstractions.Storage;

public enum ArtifactRecoveryKind { All, Staging, Committed, Uncertain, PendingReclamation }
public enum ArtifactEnumerationConsistency { Snapshot, Incomplete }
public enum ArtifactObservationKind { ActiveStaging, AbandonedStaging, Committed, Uncertain, PendingReclamation }

public sealed record ArtifactRecoveryQuery : ArtifactDiagnostic
{
    public ArtifactRecoveryQuery(ArtifactStoreIdentity store, ArtifactRecoveryKind kind, int pageSize = 100,
        ArtifactOption<string>? continuation = null)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArtifactValidation.Require(pageSize is > 0 and <= 100);
        Store = store;
        Kind = ArtifactValidation.Defined(kind);
        PageSize = pageSize;
        Continuation = continuation ?? new ArtifactOption<string>.None();
        if (Continuation is ArtifactOption<string>.Some value) { ArtifactValidation.Handle(value.Value); }
    }
    public ArtifactStoreIdentity Store { get; }
    public ArtifactRecoveryKind Kind { get; }
    public int PageSize { get; }
    public ArtifactOption<string> Continuation { get; }
}

public sealed record ArtifactRecoveryObservation : ArtifactDiagnostic
{
    public ArtifactRecoveryObservation(ArtifactObservationKind kind, Guid operationId,
        ArtifactOption<ArtifactStamp>? stamp = null, ArtifactOption<ArtifactStagingOwner>? owner = null)
    {
        Kind = ArtifactValidation.Defined(kind);
        OperationId = ArtifactValidation.Id(operationId);
        Stamp = stamp ?? new ArtifactOption<ArtifactStamp>.None();
        Owner = owner ?? new ArtifactOption<ArtifactStagingOwner>.None();
        var staging = kind is ArtifactObservationKind.ActiveStaging or ArtifactObservationKind.AbandonedStaging;
        ArtifactValidation.Require(staging
            ? Owner is ArtifactOption<ArtifactStagingOwner>.Some held && held.Value.Ticket.Id == operationId
                && Stamp is ArtifactOption<ArtifactStamp>.None
            : Owner is ArtifactOption<ArtifactStagingOwner>.None
                && (kind == ArtifactObservationKind.Uncertain || Stamp is ArtifactOption<ArtifactStamp>.Some));
    }
    public ArtifactObservationKind Kind { get; }
    public Guid OperationId { get; }
    public ArtifactOption<ArtifactStamp> Stamp { get; }
    public ArtifactOption<ArtifactStagingOwner> Owner { get; }
}

public sealed record ArtifactRecoveryPage : ArtifactDiagnostic
{
    public ArtifactRecoveryPage(IEnumerable<ArtifactRecoveryObservation> observations,
        ArtifactEnumerationConsistency consistency, ArtifactOption<string>? continuation = null)
    {
        Observations = ArtifactValidation.Collection(observations, 100);
        Consistency = ArtifactValidation.Defined(consistency);
        Continuation = continuation ?? new ArtifactOption<string>.None();
        if (Continuation is ArtifactOption<string>.Some value) { ArtifactValidation.Handle(value.Value); }
    }
    public ImmutableArray<ArtifactRecoveryObservation> Observations { get; }
    public ArtifactEnumerationConsistency Consistency { get; }
    public ArtifactOption<string> Continuation { get; }
}

public abstract record ArtifactCleanupTarget : ArtifactDiagnostic
{
    private ArtifactCleanupTarget() { }
    public sealed record AbandonedStaging : ArtifactCleanupTarget
    {
        public AbandonedStaging(ArtifactStagingOwner owner)
            => Owner = owner ?? throw new ArgumentNullException(nameof(owner));
        public ArtifactStagingOwner Owner { get; }
    }
    public sealed record RemovedIncarnation : ArtifactCleanupTarget
    {
        public RemovedIncarnation(ArtifactStamp stamp)
            => Stamp = stamp ?? throw new ArgumentNullException(nameof(stamp));
        public ArtifactStamp Stamp { get; }
    }
}

public sealed record ArtifactCleanupRequest : ArtifactDiagnostic
{
    public ArtifactCleanupRequest(ArtifactStoreIdentity store, IEnumerable<ArtifactCleanupTarget> targets)
    {
        ArgumentNullException.ThrowIfNull(store);
        Store = store;
        Targets = ArtifactValidation.Collection(targets, 100);
        ArtifactValidation.Require(Targets.Length > 0 && Targets.All(target => target switch
        {
            ArtifactCleanupTarget.AbandonedStaging value => value.Owner.Ticket.Store == store,
            ArtifactCleanupTarget.RemovedIncarnation value => value.Stamp.Store == store,
            _ => false
        }));
    }
    public ArtifactStoreIdentity Store { get; }
    public ImmutableArray<ArtifactCleanupTarget> Targets { get; }
}

public sealed record ArtifactCleanupReport : ArtifactDiagnostic
{
    public ArtifactCleanupReport(int completed, int conflicted, int pending, long reclaimedBytes)
    {
        ArtifactValidation.Require(completed >= 0 && conflicted >= 0 && pending >= 0
            && (long)completed + conflicted + pending <= 100 && reclaimedBytes >= 0);
        Completed = completed;
        Conflicted = conflicted;
        Pending = pending;
        ReclaimedBytes = reclaimedBytes;
    }
    public int Completed { get; }
    public int Conflicted { get; }
    public int Pending { get; }
    public long ReclaimedBytes { get; }
}

public enum ArtifactInitializationMode { CreateEmpty, ReopenCompatible }

public sealed record ArtifactInitialization : ArtifactDiagnostic
{
    public ArtifactInitialization(ArtifactInitializationMode mode, ArtifactStoreIdentity store,
        IArtifactCoordinationAuthority authority, ArtifactLimits? limits = null,
        ArtifactOwnershipOptions? ownership = null)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArgumentNullException.ThrowIfNull(authority);
        Mode = ArtifactValidation.Defined(mode);
        Store = store;
        Authority = authority;
        Limits = limits ?? new ArtifactLimits();
        Ownership = ownership ?? new ArtifactOwnershipOptions();
    }
    public ArtifactInitializationMode Mode { get; }
    public ArtifactStoreIdentity Store { get; }
    public IArtifactCoordinationAuthority Authority { get; }
    public ArtifactLimits Limits { get; }
    public ArtifactOwnershipOptions Ownership { get; }
}

public sealed record ArtifactAdmission : ArtifactDiagnostic
{
    public ArtifactAdmission(ArtifactStoreIdentity store, ArtifactCapabilities capabilities)
    {
        Store = store ?? throw new ArgumentNullException(nameof(store));
        Capabilities = capabilities ?? throw new ArgumentNullException(nameof(capabilities));
    }
    public ArtifactStoreIdentity Store { get; }
    public ArtifactCapabilities Capabilities { get; }
}

public sealed record ArtifactShutdown : ArtifactDiagnostic
{
    public ArtifactShutdown(ArtifactCleanupState state, int retainedTransfers, int retainedGuards, bool ready)
    {
        State = ArtifactValidation.Defined(state);
        ArtifactValidation.Require(retainedTransfers is >= 0 and <= 4 && retainedGuards >= 0
            && !ready && (state != ArtifactCleanupState.Released || retainedTransfers == 0 && retainedGuards == 0));
        RetainedTransfers = retainedTransfers;
        RetainedGuards = retainedGuards;
        Ready = ready;
    }
    public ArtifactCleanupState State { get; }
    public int RetainedTransfers { get; }
    public int RetainedGuards { get; }
    public bool Ready { get; }
}
