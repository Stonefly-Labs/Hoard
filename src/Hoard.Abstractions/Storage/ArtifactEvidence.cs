namespace Hoard.Abstractions.Storage;

public enum ArtifactPublicationOutcome { Published, AlreadyPresentVerified }

public sealed record ArtifactCommitEvidence : ArtifactDiagnostic
{
    public ArtifactCommitEvidence(ArtifactStamp stamp, Guid ticketId, Guid receiptId,
        string proofHandle, ArtifactPublicationOutcome outcome)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        Stamp = stamp;
        TicketId = ArtifactValidation.Id(ticketId);
        ReceiptId = ArtifactValidation.Id(receiptId);
        ProofHandle = ArtifactValidation.Handle(proofHandle);
        Outcome = ArtifactValidation.Defined(outcome);
    }
    public ArtifactStamp Stamp { get; }
    public Guid TicketId { get; }
    public Guid ReceiptId { get; }
    public string ProofHandle { get; }
    public ArtifactPublicationOutcome Outcome { get; }
}
