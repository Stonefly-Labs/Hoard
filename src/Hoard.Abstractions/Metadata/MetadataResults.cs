using System.Collections.Immutable;
using System.Text.Json.Serialization;

namespace Hoard.Abstractions.Metadata;

public enum MetadataFailureCode
{
    InvalidInput, Conflict, CancelledBeforeCommit, DeadlineExceeded, Unavailable, Capacity,
    CorruptState, IncompatibleSchema, Uncertain, ReconciliationExpired, Disposed, InternalFailure
}

public enum MetadataPhase { Admission, Reserve, Read, Page, Publication, Commit, Reconcile, Schema, Cleanup }
public enum MetadataRetryDisposition { CorrectInput, RetrySameTicket, Reconcile, OperatorRecovery, None }

public abstract record MetadataResult<T> : MetadataDiagnostic where T : notnull
{
    private MetadataResult() { }
    public sealed record Success : MetadataResult<T>
    {
        public Success(T value) => Value = value ?? throw new ArgumentNullException(nameof(value));
        public T Value { get; }
    }
    public sealed record Failure : MetadataResult<T>
    {
        public Failure(MetadataFailureCode code, MetadataPhase phase, MetadataRetryDisposition retry,
            MetadataId correlationId) : this(code, phase, retry, correlationId, new MetadataOption<MetadataOperationTicket>.None()) { }
        public Failure(MetadataFailureCode code, MetadataPhase phase, MetadataRetryDisposition retry,
            MetadataId correlationId, MetadataOption<MetadataOperationTicket> ticket)
        {
            MetadataValidation.Require(Enum.IsDefined(code) && Enum.IsDefined(phase) && Enum.IsDefined(retry));
            ArgumentNullException.ThrowIfNull(correlationId);
            ArgumentNullException.ThrowIfNull(ticket);
            Code = code;
            Phase = phase;
            Retry = retry;
            CorrelationId = correlationId;
            Ticket = ticket;
        }
        public MetadataFailureCode Code { get; }
        public MetadataPhase Phase { get; }
        public MetadataRetryDisposition Retry { get; }
        public MetadataId CorrelationId { get; }
        public MetadataOption<MetadataOperationTicket> Ticket { get; }
    }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$read")]
[JsonDerivedType(typeof(MetadataReadItem.Found), "found")]
[JsonDerivedType(typeof(MetadataReadItem.NotFound), "not-found")]
public abstract record MetadataReadItem : MetadataDiagnostic
{
    private MetadataReadItem() { }
    public sealed record Found(MetadataRecord Record) : MetadataReadItem;
    public sealed record NotFound(MetadataSelector Selector) : MetadataReadItem;
}

public sealed record MetadataReadSnapshot : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataReadSnapshot(ImmutableArray<MetadataReadItem> items)
    {
        Items = MetadataValidation.Collection(items, 1, 64);
        MetadataValidation.Require(items.All(item => item is not null));
    }
    public ImmutableArray<MetadataReadItem> Items { get; }
}
public sealed record MetadataPage : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataPage(ImmutableArray<MetadataRecord> records, MetadataOption<MetadataContinuation> continuation)
    {
        Records = MetadataValidation.Collection(records, 0, 100);
        ArgumentNullException.ThrowIfNull(continuation);
        MetadataValidation.Require(records.All(record => record is not null));
        Continuation = continuation;
    }
    public ImmutableArray<MetadataRecord> Records { get; }
    public MetadataOption<MetadataContinuation> Continuation { get; }
}
public sealed record MetadataTargetRevision(
    MetadataSelector Target, MetadataOption<MetadataRevision> Revision) : MetadataDiagnostic;
public sealed record MetadataReferenceObservation(
    ArtifactDigest Digest, MetadataRevision Revision, long LiveReferences) : MetadataDiagnostic;
public sealed record MetadataCommitReceipt : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataCommitReceipt(MetadataOperationTicket ticket, MetadataId commitId,
        ImmutableArray<MetadataTargetRevision> revisions, ImmutableArray<MetadataReferenceObservation> references)
    {
        MetadataEncoding.ValidateTicket(ticket);
        ArgumentNullException.ThrowIfNull(commitId);
        Revisions = MetadataValidation.Collection(revisions, 1, 64);
        References = MetadataValidation.Collection(references, 0, 128);
        MetadataValidation.Require(revisions.All(item => item is not null) && references.All(item => item is not null));
        Ticket = ticket;
        CommitId = commitId;
    }
    public MetadataOperationTicket Ticket { get; }
    public MetadataId CommitId { get; }
    public ImmutableArray<MetadataTargetRevision> Revisions { get; }
    public ImmutableArray<MetadataReferenceObservation> References { get; }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$resolution")]
[JsonDerivedType(typeof(MetadataResolution.Committed), "committed")]
[JsonDerivedType(typeof(MetadataResolution.NotCommitted), "not-committed")]
public abstract record MetadataResolution : MetadataDiagnostic
{
    private MetadataResolution() { }
    public sealed record Committed(MetadataCommitReceipt Receipt) : MetadataResolution;
    public sealed record NotCommitted(MetadataOperationTicket AbandonedTicket) : MetadataResolution;
}

public enum MetadataSchemaState { Empty, Compatible, UpgradeRequired, Incompatible }
public enum MetadataSchemaAction { CreateExplicitly, Admit, UpgradeWithRecoveryPoint, UseCompatibleApplication, Recover }
public sealed record MetadataSchemaInspection(
    MetadataSchemaState State, string ProviderId, string CurrentVersion, string TargetVersion,
    MetadataSchemaAction Action) : MetadataDiagnostic;
public sealed record MetadataSchemaAdmission(
    string ProviderId, string SchemaVersion, MetadataId Epoch, bool Durable) : MetadataDiagnostic;
public sealed record MetadataRecoveryPoint(
    MetadataId Id, MetadataId Epoch, string ProviderId, string SchemaVersion,
    string ApplicationVersion, string LogicalDigest) : MetadataDiagnostic;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$schema")]
[JsonDerivedType(typeof(MetadataSchemaRequest.InspectOnly), "inspect-only")]
[JsonDerivedType(typeof(MetadataSchemaRequest.CreateIfEmpty), "create-if-empty")]
[JsonDerivedType(typeof(MetadataSchemaRequest.Upgrade), "upgrade")]
public abstract record MetadataSchemaRequest : MetadataDiagnostic
{
    private MetadataSchemaRequest() { }
    public sealed record InspectOnly : MetadataSchemaRequest;
    public sealed record CreateIfEmpty : MetadataSchemaRequest;
    public sealed record Upgrade(
        string ExpectedCurrent, string Target, MetadataRecoveryPoint VerifiedRecoveryPoint) : MetadataSchemaRequest;
}

public sealed record MetadataCommittedArtifact(ArtifactDigest Digest, long Length) : MetadataDiagnostic;
