namespace Hoard.Abstractions.Storage;

public enum ArtifactMutationOutcome { Published, AlreadyPresentVerified, Removed, AlreadyAbsent }
public enum ArtifactVisibility { Committed, Removed }
public enum ArtifactReclamation { NotApplicable, Pending, Reclaimed }

public sealed record ArtifactMutationReceipt : ArtifactDiagnostic
{
    public ArtifactMutationReceipt(ArtifactOperationTicket ticket, Guid receiptId, ArtifactMutationOutcome outcome,
        ArtifactStamp stamp, ArtifactVisibility visibility, ArtifactReclamation reclamation,
        ArtifactOption<ArtifactCommitEvidence>? evidence = null)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(stamp);
        ArtifactValidation.Require(ticket.Store == stamp.Store);
        Ticket = ticket;
        ReceiptId = ArtifactValidation.Id(receiptId);
        Outcome = ArtifactValidation.Defined(outcome);
        Stamp = stamp;
        Visibility = ArtifactValidation.Defined(visibility);
        Reclamation = ArtifactValidation.Defined(reclamation);
        Evidence = evidence ?? new ArtifactOption<ArtifactCommitEvidence>.None();
        var publication = outcome is ArtifactMutationOutcome.Published or ArtifactMutationOutcome.AlreadyPresentVerified;
        ArtifactValidation.Require(publication
            ? ticket.Kind == ArtifactOperationKind.Write && visibility == ArtifactVisibility.Committed
                && reclamation == ArtifactReclamation.NotApplicable
                && Evidence is ArtifactOption<ArtifactCommitEvidence>.Some proof
                && proof.Value.Stamp == stamp && proof.Value.TicketId == ticket.Id
                && proof.Value.ReceiptId == receiptId
                && (int)proof.Value.Outcome == (int)outcome
            : ticket.Kind == ArtifactOperationKind.Delete && visibility == ArtifactVisibility.Removed
                && reclamation is ArtifactReclamation.Pending or ArtifactReclamation.Reclaimed
                && Evidence is ArtifactOption<ArtifactCommitEvidence>.None);
    }
    public ArtifactOperationTicket Ticket { get; }
    public Guid ReceiptId { get; }
    public ArtifactMutationOutcome Outcome { get; }
    public ArtifactStamp Stamp { get; }
    public ArtifactVisibility Visibility { get; }
    public ArtifactReclamation Reclamation { get; }
    public ArtifactOption<ArtifactCommitEvidence> Evidence { get; }
}

public abstract record ArtifactResolution : ArtifactDiagnostic
{
    private ArtifactResolution() { }
    public sealed record Pending : ArtifactResolution
    {
        public Pending(ArtifactOperationTicket ticket) => Ticket = ticket ?? throw new ArgumentNullException(nameof(ticket));
        public ArtifactOperationTicket Ticket { get; }
    }
    public sealed record NotCommitted : ArtifactResolution
    {
        public NotCommitted(ArtifactOperationTicket ticket) => Ticket = ticket ?? throw new ArgumentNullException(nameof(ticket));
        public ArtifactOperationTicket Ticket { get; }
    }
    public sealed record Committed : ArtifactResolution
    {
        public Committed(ArtifactMutationReceipt receipt)
        {
            ArgumentNullException.ThrowIfNull(receipt);
            ArtifactValidation.Require(receipt.Visibility == ArtifactVisibility.Committed);
            Receipt = receipt;
        }
        public ArtifactMutationReceipt Receipt { get; }
    }
    public sealed record Removed : ArtifactResolution
    {
        public Removed(ArtifactMutationReceipt receipt)
        {
            ArgumentNullException.ThrowIfNull(receipt);
            ArtifactValidation.Require(receipt.Outcome == ArtifactMutationOutcome.Removed);
            Receipt = receipt;
        }
        public ArtifactMutationReceipt Receipt { get; }
    }
    public sealed record AlreadyAbsent : ArtifactResolution
    {
        public AlreadyAbsent(ArtifactMutationReceipt receipt)
        {
            ArgumentNullException.ThrowIfNull(receipt);
            ArtifactValidation.Require(receipt.Outcome == ArtifactMutationOutcome.AlreadyAbsent);
            Receipt = receipt;
        }
        public ArtifactMutationReceipt Receipt { get; }
    }
}
