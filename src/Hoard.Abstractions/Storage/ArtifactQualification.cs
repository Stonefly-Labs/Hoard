using System.Collections.Immutable;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace Hoard.Abstractions.Storage;

public enum ArtifactQualificationCaseStatus { Passed, NotApplicable }

public sealed record ArtifactQualificationCaseResult : ArtifactDiagnostic
{
    public ArtifactQualificationCaseResult(string caseId, ArtifactQualificationCaseStatus status,
        TimeSpan duration, IEnumerable<string> proofHashes)
    {
        ArgumentNullException.ThrowIfNull(caseId);
        ArtifactValidation.Require(caseId.Length == 5 && caseId.StartsWith("AS-", StringComparison.Ordinal)
            && int.TryParse(caseId.AsSpan(3), NumberStyles.None, CultureInfo.InvariantCulture, out var number)
            && number is >= 1 and <= 48 && duration >= TimeSpan.Zero);
        CaseId = caseId;
        Status = ArtifactValidation.Defined(status);
        Duration = duration;
        ProofHashes = ArtifactValidation.Collection(proofHashes, 32);
        ArtifactValidation.Require(ProofHashes.Length > 0 && ProofHashes.Distinct().Count() == ProofHashes.Length);
        foreach (var hash in ProofHashes) { ArtifactValidation.Sha256(hash); }
    }
    public string CaseId { get; }
    public ArtifactQualificationCaseStatus Status { get; }
    public TimeSpan Duration { get; }
    public ImmutableArray<string> ProofHashes { get; }
}

public sealed record ArtifactQualificationEnvironment : ArtifactDiagnostic
{
    public ArtifactQualificationEnvironment(string operatingSystem, string runtime, string fileSystem, string flushConfiguration)
    {
        OperatingSystem = Label(operatingSystem);
        Runtime = Label(runtime);
        FileSystem = Label(fileSystem);
        FlushConfiguration = Label(flushConfiguration);
        Sha256 = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(
            string.Join('\n', OperatingSystem, Runtime, FileSystem, FlushConfiguration))));
    }
    public string OperatingSystem { get; }
    public string Runtime { get; }
    public string FileSystem { get; }
    public string FlushConfiguration { get; }
    public string Sha256 { get; }

    private static string Label(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        ArtifactValidation.Require(value.Length is > 0 and <= 256 && value.Any(character => character != ' ')
            && value.All(character => character is >= ' ' and <= '~'));
        return value;
    }
}

public sealed record ArtifactQualificationRecord : ArtifactDiagnostic
{
    public ArtifactQualificationRecord(string implementationId, string packageVersion, string packageSha256,
        string configurationSha256, string sourceSha256, string lockSha256, string environmentSha256,
        ArtifactCapabilities capabilities, IEnumerable<string> caseIds, IEnumerable<string> proofHashes,
        IEnumerable<string> exclusions)
        => throw new ArgumentException("Qualification requires an explicit environment and per-case results.");

    public ArtifactQualificationRecord(string implementationId, string packageVersion, string packageSha256,
        string configurationSha256, string sourceSha256, string lockSha256,
        ArtifactQualificationEnvironment environment, ArtifactCapabilities capabilities,
        IEnumerable<ArtifactQualificationCaseResult> caseResults)
    {
        ImplementationId = ArtifactValidation.Handle(implementationId);
        PackageVersion = ArtifactValidation.Handle(packageVersion);
        PackageSha256 = ArtifactValidation.Sha256(packageSha256);
        ConfigurationSha256 = ArtifactValidation.Sha256(configurationSha256);
        SourceSha256 = ArtifactValidation.Sha256(sourceSha256);
        LockSha256 = ArtifactValidation.Sha256(lockSha256);
        Environment = environment ?? throw new ArgumentNullException(nameof(environment));
        Capabilities = capabilities ?? throw new ArgumentNullException(nameof(capabilities));
        ArtifactValidation.Require(capabilities.MeetsBaseline);
        CaseResults = ArtifactValidation.Collection(caseResults, 48);
        CaseIds = CaseResults.Select(result => result.CaseId).ToImmutableArray();
        ArtifactValidation.Require(CaseIds.Length == 48 && CaseIds.Distinct().Count() == 48);
        foreach (var result in CaseResults)
        {
            var excluded = capabilities.Durability == ArtifactDurability.SimulationOnly
                && result.CaseId is "AS-41" or "AS-42" or "AS-43" or "AS-44";
            ArtifactValidation.Require(result.Status == (excluded
                ? ArtifactQualificationCaseStatus.NotApplicable : ArtifactQualificationCaseStatus.Passed));
        }
        ProofHashes = CaseResults.SelectMany(result => result.ProofHashes).Distinct(StringComparer.Ordinal).ToImmutableArray();
        ArtifactValidation.Require(ProofHashes.Length <= 256);
        Exclusions = CaseResults.Where(result => result.Status == ArtifactQualificationCaseStatus.NotApplicable)
            .Select(result => result.CaseId).Order(StringComparer.Ordinal).ToImmutableArray();
    }
    public string ImplementationId { get; }
    public string PackageVersion { get; }
    public string PackageSha256 { get; }
    public string ConfigurationSha256 { get; }
    public string SourceSha256 { get; }
    public string LockSha256 { get; }
    public ArtifactQualificationEnvironment Environment { get; }
    public string EnvironmentSha256 => Environment.Sha256;
    public ArtifactCapabilities Capabilities { get; }
    public ImmutableArray<ArtifactQualificationCaseResult> CaseResults { get; }
    public ImmutableArray<string> CaseIds { get; }
    public ImmutableArray<string> ProofHashes { get; }
    public ImmutableArray<string> Exclusions { get; }
}
