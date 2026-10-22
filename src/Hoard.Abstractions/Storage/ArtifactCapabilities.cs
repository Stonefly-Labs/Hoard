using System.Collections.Immutable;

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

public sealed record ArtifactQualificationRecord : ArtifactDiagnostic
{
    public ArtifactQualificationRecord(string implementationId, string packageVersion, string packageSha256,
        string configurationSha256, string sourceSha256, string lockSha256, string environmentSha256,
        ArtifactCapabilities capabilities, IEnumerable<string> caseIds, IEnumerable<string> proofHashes,
        IEnumerable<string> exclusions)
    {
        ImplementationId = ArtifactValidation.Handle(implementationId);
        PackageVersion = ArtifactValidation.Handle(packageVersion);
        foreach (var hash in new[] { packageSha256, configurationSha256, sourceSha256, lockSha256, environmentSha256 })
        { ValidateHash(hash); }
        PackageSha256 = packageSha256;
        ConfigurationSha256 = configurationSha256;
        SourceSha256 = sourceSha256;
        LockSha256 = lockSha256;
        EnvironmentSha256 = environmentSha256;
        Capabilities = capabilities ?? throw new ArgumentNullException(nameof(capabilities));
        CaseIds = ArtifactValidation.Collection(caseIds, 48);
        ProofHashes = ArtifactValidation.Collection(proofHashes, 256);
        Exclusions = ArtifactValidation.Collection(exclusions, 4);
        ArtifactValidation.Require(CaseIds.Length == 48 && CaseIds.Distinct().Count() == 48
            && CaseIds.Order(StringComparer.Ordinal).SequenceEqual(Enumerable.Range(1, 48).Select(number => $"AS-{number:D2}")));
        foreach (var hash in ProofHashes) { ValidateHash(hash); }
        ArtifactValidation.Require(ProofHashes.Length > 0
            && Exclusions.All(value => value is "AS-41" or "AS-42" or "AS-43" or "AS-44")
            && Exclusions.Distinct().Count() == Exclusions.Length
            && Exclusions.Length == (capabilities.Durability == ArtifactDurability.SimulationOnly ? 4 : 0));
    }
    private static void ValidateHash(string hash)
    {
        ArgumentNullException.ThrowIfNull(hash);
        ArtifactValidation.Require(hash.Length == 64
            && hash.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f'));
    }
    public string ImplementationId { get; }
    public string PackageVersion { get; }
    public string PackageSha256 { get; }
    public string ConfigurationSha256 { get; }
    public string SourceSha256 { get; }
    public string LockSha256 { get; }
    public string EnvironmentSha256 { get; }
    public ArtifactCapabilities Capabilities { get; }
    public ImmutableArray<string> CaseIds { get; }
    public ImmutableArray<string> ProofHashes { get; }
    public ImmutableArray<string> Exclusions { get; }
}
