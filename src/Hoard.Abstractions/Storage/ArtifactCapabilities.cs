namespace Hoard.Abstractions.Storage;

public enum ArtifactDurability { LocalProcessCrash, SimulationOnly }
public enum ArtifactVisibilityGuarantee { DirectBeforeAcknowledgment }
public enum ArtifactVerificationPolicy { InputReuseAndEveryFullRead }

public sealed record ArtifactCapabilities : ArtifactDiagnostic
{
    public ArtifactCapabilities(int version, ArtifactDurability durability, ArtifactEnumerationConsistency enumeration,
        ArtifactLimits limits, bool conditionalPublication = true, bool conditionalDeletion = true,
        bool stagingRecovery = true, bool ownerFencing = true, bool readerProtection = true,
        bool boundedStreaming = true, bool rangeReads = false, bool sha512 = true)
    {
        ArtifactValidation.Require(version > 0);
        ArgumentNullException.ThrowIfNull(limits);
        Version = version;
        Durability = ArtifactValidation.Defined(durability);
        Enumeration = ArtifactValidation.Defined(enumeration);
        Limits = limits;
        ConditionalPublication = conditionalPublication;
        ConditionalDeletion = conditionalDeletion;
        StagingRecovery = stagingRecovery;
        OwnerFencing = ownerFencing;
        ReaderProtection = readerProtection;
        BoundedStreaming = boundedStreaming;
        RangeReads = rangeReads;
        Sha512 = sha512;
    }
    public int Version { get; }
    public ArtifactDurability Durability { get; }
    public ArtifactEnumerationConsistency Enumeration { get; }
    public ArtifactLimits Limits { get; }
    public ArtifactVisibilityGuarantee Visibility => ArtifactVisibilityGuarantee.DirectBeforeAcknowledgment;
    public ArtifactVerificationPolicy Verification => ArtifactVerificationPolicy.InputReuseAndEveryFullRead;
    public TimeSpan TicketLifetime => TimeSpan.FromHours(24);
    public bool ConditionalPublication { get; }
    public bool ConditionalDeletion { get; }
    public bool StagingRecovery { get; }
    public bool OwnerFencing { get; }
    public bool ReaderProtection { get; }
    public bool BoundedStreaming { get; }
    public bool RangeReads { get; }
    public bool Sha512 { get; }
    public bool MeetsBaseline => Version == 1 && ConditionalPublication && ConditionalDeletion && StagingRecovery
        && OwnerFencing && ReaderProtection && BoundedStreaming;
}
