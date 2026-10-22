using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

internal sealed class LocalOperation
{
    public Guid Id { get; set; }
    public DateTimeOffset Issued { get; set; }
    public DateTimeOffset Expires { get; set; }
    public string Fingerprint { get; set; } = "";
    public ArtifactOperationKind Kind { get; set; }
    public long Cap { get; set; }
    public string? ExpectedDigest { get; set; }
    public long? ExpectedLength { get; set; }
    public string? ExpectedChecksum { get; set; }
    public Guid Session { get; set; }
    public Guid Owner { get; set; }
    public long Generation { get; set; }
    public DateTimeOffset OwnerExpires { get; set; }
    public Guid Verified { get; set; }
    public LocalContent? Content { get; set; }
    private string state = "reserved";
    public string State { get => Volatile.Read(ref state); set => Volatile.Write(ref state, value); }
    public Guid Receipt { get; set; }
    public string Proof { get; set; } = "";
    public ArtifactMutationOutcome Outcome { get; set; }
    public ArtifactReclamation Reclamation { get; set; }
    public bool ReservationReleased { get; set; }
}

internal sealed record LocalContent(string Digest, long Length, Guid Incarnation)
{
    public ArtifactStamp Stamp(ArtifactStoreIdentity store)
        => new(store, new ArtifactIdentity(new ArtifactDigest(Digest), Length), Incarnation);
}

internal sealed record LocalDecision(LocalContent Content, Guid Operation, bool Removed = false,
    bool Reclaimed = false, bool Corrupt = false);
