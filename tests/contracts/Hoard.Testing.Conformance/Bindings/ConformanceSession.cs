using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Bindings;

public enum ConformanceOwnershipState { Allocated, Active, Settling, Released, Retained }

public sealed class ConformanceCleanupObservation
{
    public ConformanceCleanupObservation(ConformanceOwnershipState state, IEnumerable<string> resourceIds)
    {
        if (!Enum.IsDefined(state)) { throw new ArgumentException("OwnershipInvalid"); }
        ArgumentNullException.ThrowIfNull(resourceIds);
        State = state;
        ResourceIds = resourceIds.Take(1025).Select(ConformanceBindingDeclaration.Id).ToImmutableArray();
        if (ResourceIds.Length > 1024 || ResourceIds.Distinct(StringComparer.Ordinal).Count() != ResourceIds.Length
            || (state == ConformanceOwnershipState.Retained && ResourceIds.IsEmpty))
        { throw new ArgumentException("OwnershipInvalid"); }
    }

    public ConformanceOwnershipState State { get; }
    public ImmutableArray<string> ResourceIds { get; }
}

public sealed record ConformanceFaultObservation(
    ConformanceFault Fault, string BoundaryId, long ObservationCount,
    ConformanceOwnershipState Ownership);

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

public interface IMetadataConformanceAuthority : IMetadataPublicationAuthority
{
    MetadataArtifactEvidence Register(ArtifactDigest digest, long length);
}

public interface IMetadataConformanceFaultDriver : IConformanceFaultDriver
{
    ValueTask<IMetadataCorruptionScope> CorruptAsync(
        MetadataCorruptionRequest request, CancellationToken cancellationToken);
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
        MetadataSelector Selector, MetadataRecordCorruption Corruption) : MetadataCorruptionRequest;
    public sealed record Operation(
        MetadataOperationTicket Ticket, MetadataOperationCorruption Corruption,
        MetadataOperationTicket ForeignTicket) : MetadataCorruptionRequest;
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
    ValueTask DamagePayloadAsync(bool truncate, CancellationToken cancellationToken);
    ValueTask AwaitSettlementAsync(CancellationToken cancellationToken);
}
