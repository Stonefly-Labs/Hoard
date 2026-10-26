using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Diagnostics;

namespace Hoard.Testing.Conformance.Bindings;

public enum ConformanceOwnershipState { Allocated, Active, Settling, Released, Retained }

public sealed class ConformanceCleanupObservation
{
    public ConformanceCleanupObservation(ConformanceOwnershipState state, IEnumerable<string> resourceIds,
        ConformanceDiagnosticCode reason = ConformanceDiagnosticCode.None)
    {
        if (!Enum.IsDefined(state) || !Enum.IsDefined(reason)) { throw new ArgumentException("OwnershipInvalid"); }
        ArgumentNullException.ThrowIfNull(resourceIds);
        State = state;
        ResourceIds = resourceIds.Take(1025).Select(ConformanceBindingDeclaration.Id).ToImmutableArray();
        if (ResourceIds.Length > 1024 || ResourceIds.Distinct(StringComparer.Ordinal).Count() != ResourceIds.Length
            || (state == ConformanceOwnershipState.Retained
                && (ResourceIds.IsEmpty || reason == ConformanceDiagnosticCode.None))
            || (state == ConformanceOwnershipState.Released
                && (!ResourceIds.IsEmpty || reason != ConformanceDiagnosticCode.None)))
        { throw new ArgumentException("OwnershipInvalid"); }
        Reason = reason;
    }

    public ConformanceOwnershipState State { get; }
    public ImmutableArray<string> ResourceIds { get; }
    public ConformanceDiagnosticCode Reason { get; }
}

public sealed record ConformanceFaultObservation(
    ConformanceFault Fault, string BoundaryId, long ObservationCount,
    ConformanceOwnershipState Ownership)
{
    public ConformanceFault Fault { get; } = Enum.IsDefined(Fault) ? Fault : throw new ArgumentException("BindingInvalid");
    public string BoundaryId { get; } = ConformanceBindingDeclaration.Id(BoundaryId);
    public long ObservationCount { get; } = ObservationCount >= 0
        ? ObservationCount : throw new ArgumentException("BindingInvalid");
    public ConformanceOwnershipState Ownership { get; } = Enum.IsDefined(Ownership)
        ? Ownership : throw new ArgumentException("OwnershipInvalid");
}

public interface IConformanceFaultDriver
{
    ImmutableArray<ConformanceFault> SupportedFaults { get; }
    ValueTask ArmAsync(ConformanceFault fault, CancellationToken cancellationToken);
    ValueTask WaitForBoundaryAsync(ConformanceFault fault, CancellationToken cancellationToken);
    ValueTask ReleaseAsync(ConformanceFault fault, CancellationToken cancellationToken);
    ValueTask<ConformanceFaultObservation> ObserveAsync(ConformanceFault fault, CancellationToken cancellationToken);
}

public interface IMetadataConformanceSession : IAsyncDisposable
{
    IMetadataStore Store { get; }
    IMetadataSchemaAdministration Schema { get; }
    IMetadataConformanceAuthority Authority { get; }
    IMetadataConformanceFaultDriver Faults { get; }
    ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken);
    ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken);
}

/// <summary>An owned schema-assertion projection, not admission as a complete category binding.</summary>
public interface IMetadataSchemaAssertionSession : IAsyncDisposable
{
    IMetadataStore Store { get; }
    IMetadataSchemaAdministration Schema { get; }
    IMetadataConformanceAuthority Authority { get; }
    ValueTask<IMetadataSchemaAssertionSession> ReopenAsync(CancellationToken cancellationToken);
    ValueTask<ConformanceStateFingerprint> ObserveStateAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutAsync(bool partial, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> SetFutureSchemaAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(MetadataSelector selector, CancellationToken cancellationToken);
    ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync(CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        MetadataObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken);
    ValueTask AwaitSettlementAsync(CancellationToken cancellationToken);
}

public interface IMetadataConformanceAuthority : IMetadataPublicationAuthority
{
    int Acquisitions { get; }
    int ActiveGuards { get; }
    MetadataArtifactEvidence Register(ArtifactDigest digest, long length);
    void Revoke(MetadataArtifactEvidence evidence);
}

public interface IMetadataConformanceFaultDriver : IConformanceFaultDriver
{
    MetadataFaultCounters Counters { get; }
    ValueTask<ConformanceStateFingerprint> ObserveStateAsync(CancellationToken cancellationToken);
    ValueTask<MetadataContinuation> CorruptContinuationAsync(
        MetadataContinuation continuation, MetadataContinuationComponent component,
        MetadataContinuationCorruption corruption, CancellationToken cancellationToken);
    /// <summary>Disposes the observation registration, not the store work that may already be invoking it.</summary>
    ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        MetadataObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken);
    ValueTask<IMetadataCorruptionScope> CorruptAsync(
        MetadataCorruptionRequest request, CancellationToken cancellationToken);
    ValueTask RestoreCorruptionsAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotAsync(
        MetadataReadGroup request, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> HoldWriterAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> FillLedgerAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(MetadataSelector selector, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationAsync(
        CanonicalText resource, long generation, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> SetFutureSchemaAsync(CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutAsync(bool partial, CancellationToken cancellationToken);
    ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync(CancellationToken cancellationToken);
    ValueTask AwaitSettlementAsync(CancellationToken cancellationToken);
}

public enum MetadataRecordCorruption
{
    NullLabel, OversizedLabel, NullRevision, MalformedEncoding, MismatchedKey,
    CacheAuthorization, AggregateAuthorization, AggregateStart, AggregateEnd, LeaseResource
}

public enum MetadataOperationCorruption
{
    NullTarget, NullRevision, MalformedEncoding, MissingRevisions, OversizedRevisions,
    OversizedEncoding, MismatchedTicket, MissingReceipt, ShortFingerprint,
    MissingFingerprint, InvalidFingerprintEncoding, ReservedReceipt, AbandonedReceipt,
    InvalidState
}

public abstract record MetadataCorruptionRequest
{
    private MetadataCorruptionRequest() { }
    public sealed record Record(
        MetadataSelector Selector, MetadataRecordCorruption Corruption) : MetadataCorruptionRequest
    {
        public MetadataSelector Selector { get; } = Selector ?? throw new ArgumentException("BindingInvalid");
        public MetadataRecordCorruption Corruption { get; } = Enum.IsDefined(Corruption)
            ? Corruption : throw new ArgumentException("BindingInvalid");
    }
    public sealed record Operation(
        MetadataOperationTicket Ticket, MetadataOperationCorruption Corruption,
        MetadataOperationTicket ForeignTicket) : MetadataCorruptionRequest
    {
        public MetadataOperationTicket Ticket { get; } = Ticket ?? throw new ArgumentException("BindingInvalid");
        public MetadataOperationCorruption Corruption { get; } = Enum.IsDefined(Corruption)
            ? Corruption : throw new ArgumentException("BindingInvalid");
        public MetadataOperationTicket ForeignTicket { get; } = ForeignTicket ?? throw new ArgumentException("BindingInvalid");
    }
}

public interface IMetadataCorruptionScope : IAsyncDisposable
{
    ConformanceStateFingerprint Original { get; }
    ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken);
}

public sealed record ConformanceStateFingerprint
{
    public ConformanceStateFingerprint(string sha256) => Sha256 = ConformanceBindingDeclaration.Hash(sha256);
    public string Sha256 { get; }
}

public enum ArtifactObservationPoint
{
    StagePrefix, StageVerified, PublicationAdmitted, BeforePublicationDecision,
    PublicationSelected, ReceiptPersisted, ReadOpened, ReadCopy, DeleteRemoved,
    DeleteReclaimed, CleanupCandidate, TransferQueued, BeforeReconciliation,
    ReconciliationVerified, OperationReleased, OperationCompleted, OperationReclaim, PayloadDamage,
    DirectVerification, CommitProgress, PayloadSelected
}

public enum ArtifactStorageArea { Staging, Payloads }
public sealed record ArtifactStorageFile(string Id, long Length);
public sealed record ArtifactStorageObservation(
    ImmutableArray<ArtifactStorageFile> Staging, ImmutableArray<ArtifactStorageFile> Payloads);

/// <summary>An owned assertion projection, not admission as a complete artifact category binding.</summary>
public interface IArtifactAssertionSession : IAsyncDisposable
{
    IArtifactStore Store { get; }
    IArtifactEvidenceValidator Validator { get; }
    IArtifactMaintenance Maintenance { get; }
    IArtifactStoreLifetime Lifetime { get; }
    IArtifactCoordinationAuthority Authority { get; }
    ArtifactStoreIdentity Identity { get; }
    bool Ready { get; }
    ArtifactInitializationObservation ObserveInitialization();
    int WaitingAuthorityAdmissions { get; }
    /// <summary>Reopens Local compatibly; Object simulation restarts empty with a fresh epoch and authority.</summary>
    ValueTask<IArtifactAssertionSession> ReopenAsync(CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        ArtifactObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> ObserveHistoryCandidatesAsync(
        Action<string, string> observer, CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectHistoryCandidateFailureAsync(CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectObservationFailureAsync(
        ArtifactObservationPoint point, Func<ValueTask> beforeFailure, CancellationToken cancellationToken);
    /// <summary>Interrupts an exact Local record-write occurrence; Object rejects this unsupported boundary.</summary>
    ValueTask<IArtifactFaultRegistration> InjectRecordWriteFailureAsync(
        int occurrence, Action beforeFailure, CancellationToken cancellationToken);
    /// <summary>Injects an ENOSPC-shaped storage exception after a real staging prefix write, not actual disk exhaustion.</summary>
    ValueTask<IArtifactFaultRegistration> InjectCapacityFailureAsync(CancellationToken cancellationToken);
    /// <summary>Fails the actual indexed cleanup of a result that was not delivered to its caller.</summary>
    ValueTask<IArtifactFaultRegistration> InjectUnclaimedCleanupFailureAsync(CancellationToken cancellationToken);
    /// <summary>Loses acknowledgment after real publication selection without treating the injected exception as an unexpected observer failure.</summary>
    ValueTask<IArtifactFaultRegistration> InjectPublicationAcknowledgmentLossAsync(CancellationToken cancellationToken);
    /// <summary>Holds a real synchronous fixture boundary; reserve the deletion ticket before arming. Not a stalled filesystem syscall.</summary>
    ValueTask<IArtifactSynchronousHold> HoldSynchronousStorageAsync(CancellationToken cancellationToken);
    /// <summary>Damages the exact current payload through owned fixture work; it does not change receipt or quarantine state.</summary>
    ValueTask DamagePayloadAsync(ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken);
    ValueTask<byte[]> CapturePayloadAsync(ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken);
    ValueTask ReplacePayloadAsync(ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken);
    ValueTask RemovePayloadAsync(ArtifactStamp stamp, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictPayloadAccessAsync(
        ArtifactStamp stamp, bool unavailable, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictRecordWritesAsync(CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictStorageCleanupAsync(ArtifactStorageArea area, CancellationToken cancellationToken);
    ValueTask<ArtifactStorageObservation> ObserveStorageAsync(CancellationToken cancellationToken);
    /// <summary>Joins current provider workers; this does not close authority admission or release owned roots.</summary>
    ValueTask AwaitSettlementAsync(CancellationToken cancellationToken);
    ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken);
}

public interface IArtifactFaultRegistration : IAsyncDisposable
{
    long ObservationCount { get; }
    ValueTask WaitForEntryAsync(CancellationToken cancellationToken);
}

public interface IArtifactSynchronousHold : IArtifactFaultRegistration
{
    void Release();
}

public interface IArtifactConformanceSession : IAsyncDisposable
{
    IArtifactStore Store { get; }
    IArtifactEvidenceValidator Validator { get; }
    IArtifactMaintenance Maintenance { get; }
    IArtifactStoreLifetime Lifetime { get; }
    IArtifactCoordinationAuthority Authority { get; }
    ArtifactStoreIdentity Identity { get; }
    IArtifactConformanceFaultDriver Faults { get; }
    ValueTask<IArtifactConformanceSession> ReopenAsync(CancellationToken cancellationToken);
    ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken);
}

public interface IArtifactConformanceFaultDriver : IConformanceFaultDriver
{
    ArtifactInitializationObservation ObserveInitialization();
    int WaitingAuthorityAdmissions { get; }
    IArtifactBorrowedStream BorrowedSource { get; }
    IArtifactBorrowedStream BorrowedDestination { get; }
    ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        ArtifactObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> ObserveHistoryCandidatesAsync(
        Action<string, string> observer, CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectHistoryCandidateFailureAsync(CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectObservationFailureAsync(
        ArtifactObservationPoint point, Func<ValueTask> beforeFailure, CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectRecordWriteFailureAsync(
        int occurrence, Action beforeFailure, CancellationToken cancellationToken);
    ValueTask<IArtifactFaultRegistration> InjectPublicationAcknowledgmentLossAsync(CancellationToken cancellationToken);
    ValueTask DamagePayloadAsync(ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken);
    ValueTask<byte[]> CapturePayloadAsync(ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken);
    ValueTask ReplacePayloadAsync(ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken);
    ValueTask RemovePayloadAsync(ArtifactStamp stamp, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictPayloadAccessAsync(
        ArtifactStamp stamp, bool unavailable, CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictRecordWritesAsync(CancellationToken cancellationToken);
    ValueTask<IAsyncDisposable> RestrictStorageCleanupAsync(ArtifactStorageArea area, CancellationToken cancellationToken);
    ValueTask<ArtifactStorageObservation> ObserveStorageAsync(CancellationToken cancellationToken);
    ValueTask AwaitSettlementAsync(CancellationToken cancellationToken);
}

public interface IArtifactBorrowedStream
{
    Stream Stream { get; }
    bool WasDisposed { get; }
}
