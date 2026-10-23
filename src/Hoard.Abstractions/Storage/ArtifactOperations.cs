namespace Hoard.Abstractions.Storage;

public enum ArtifactOperationKind { Write, Delete }

public sealed record ArtifactOperationTicket : ArtifactDiagnostic
{
    public ArtifactOperationTicket(ArtifactStoreIdentity store, Guid id, ArtifactOperationKind kind,
        DateTimeOffset issued, DateTimeOffset expires, string intentFingerprint)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArgumentNullException.ThrowIfNull(intentFingerprint);
        ArtifactValidation.Require(issued.Offset == TimeSpan.Zero && expires.Offset == TimeSpan.Zero
            && issued >= DateTimeOffset.UnixEpoch && expires > issued
            && expires - issued == TimeSpan.FromHours(24)
            && intentFingerprint.Length == 64
            && intentFingerprint.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f'));
        Store = store;
        Id = ArtifactValidation.Id(id);
        Kind = ArtifactValidation.Defined(kind);
        Issued = issued;
        Expires = expires;
        IntentFingerprint = intentFingerprint;
    }
    public ArtifactStoreIdentity Store { get; }
    public Guid Id { get; }
    public ArtifactOperationKind Kind { get; }
    public DateTimeOffset Issued { get; }
    public DateTimeOffset Expires { get; }
    public string IntentFingerprint { get; }
}

public sealed record ArtifactWriteIntent : ArtifactDiagnostic
{
    public ArtifactWriteIntent(ArtifactExpectations expectations)
        => Expectations = expectations ?? throw new ArgumentNullException(nameof(expectations));
    public ArtifactExpectations Expectations { get; }
}

public sealed record ArtifactDeleteIntent : ArtifactDiagnostic
{
    public ArtifactDeleteIntent(ArtifactStamp target)
        => Target = target ?? throw new ArgumentNullException(nameof(target));
    public ArtifactStamp Target { get; }
}

public sealed record ArtifactStagingOwner : ArtifactDiagnostic
{
    public ArtifactStagingOwner(ArtifactOperationTicket ticket, Guid sessionId, Guid ownerId,
        long generation, DateTimeOffset expires)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArtifactValidation.Require(ticket.Kind == ArtifactOperationKind.Write && generation > 0
            && expires.Offset == TimeSpan.Zero && expires > ticket.Issued && expires <= ticket.Expires);
        Ticket = ticket;
        SessionId = ArtifactValidation.Id(sessionId);
        OwnerId = ArtifactValidation.Id(ownerId);
        Generation = generation;
        Expires = expires;
    }
    public ArtifactOperationTicket Ticket { get; }
    public Guid SessionId { get; }
    public Guid OwnerId { get; }
    public long Generation { get; }
    public DateTimeOffset Expires { get; }
}

public sealed record ArtifactStagedWrite : ArtifactDiagnostic
{
    public ArtifactStagedWrite(ArtifactStagingOwner owner, ArtifactIdentity identity,
        Guid verifiedCompletion, string privateHandle)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(identity);
        Owner = owner;
        Identity = identity;
        VerifiedCompletion = ArtifactValidation.Id(verifiedCompletion);
        PrivateHandle = ArtifactValidation.Handle(privateHandle);
    }
    public ArtifactStagingOwner Owner { get; }
    public ArtifactIdentity Identity { get; }
    public Guid VerifiedCompletion { get; }
    public string PrivateHandle { get; }
}
