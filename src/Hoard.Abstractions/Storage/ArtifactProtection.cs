using Hoard.Abstractions.Metadata;

namespace Hoard.Abstractions.Storage;

public enum ArtifactProtectionOperation { Publication, Read, Reference, Deletion }
public enum ArtifactProtectionMode { Shared, Exclusive }

public sealed record ArtifactProtectionRequest : ArtifactDiagnostic
{
    public ArtifactProtectionRequest(Guid operationId, ArtifactProtectionOperation operation,
        ArtifactStoreIdentity store, ArtifactDigest digest, ArtifactOption<ArtifactStamp>? stamp = null)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArgumentNullException.ThrowIfNull(digest);
        OperationId = ArtifactValidation.Id(operationId);
        Operation = ArtifactValidation.Defined(operation);
        Store = store;
        Digest = digest;
        Stamp = stamp ?? new ArtifactOption<ArtifactStamp>.None();
        ArtifactValidation.Require(Stamp is not ArtifactOption<ArtifactStamp>.Some target
            || (target.Value.Store == store && target.Value.Identity.Digest == digest));
        ArtifactValidation.Require(operation is ArtifactProtectionOperation.Publication or ArtifactProtectionOperation.Read
            || Stamp is ArtifactOption<ArtifactStamp>.Some);
    }
    public Guid OperationId { get; }
    public ArtifactProtectionOperation Operation { get; }
    public ArtifactProtectionMode Mode => Operation == ArtifactProtectionOperation.Deletion
        ? ArtifactProtectionMode.Exclusive : ArtifactProtectionMode.Shared;
    public ArtifactStoreIdentity Store { get; }
    public ArtifactDigest Digest { get; }
    public ArtifactOption<ArtifactStamp> Stamp { get; }
}

public sealed record ArtifactProtectionGrant : ArtifactDiagnostic
{
    public ArtifactProtectionGrant(Guid authorityInstance, ArtifactProtectionRequest request,
        long generation, DateTimeOffset admissionExpiry)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArtifactValidation.Require(generation > 0 && admissionExpiry.Offset == TimeSpan.Zero
            && admissionExpiry > DateTimeOffset.UnixEpoch);
        AuthorityInstance = ArtifactValidation.Id(authorityInstance);
        Request = request;
        Generation = generation;
        AdmissionExpiry = admissionExpiry;
    }
    public Guid AuthorityInstance { get; }
    public ArtifactProtectionRequest Request { get; }
    public long Generation { get; }
    public DateTimeOffset AdmissionExpiry { get; }
}
