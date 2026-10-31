using System.Text.RegularExpressions;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;

namespace Hoard.Testing.Conformance.Evidence;

public sealed partial class ConformanceRuntimeWitness
{
    public ConformanceRuntimeWitness(Guid executionId, Guid runId, Guid invocationGroupId,
        ConformanceExpectedCase expected, string testIdentity, string packageSha256,
        string assemblySha256, string inputSha256, TimeSpan started, TimeSpan ended,
        ConformanceWitnessStatus status, string proofSha256)
    {
        ArgumentNullException.ThrowIfNull(expected);
        if (executionId == Guid.Empty || runId == Guid.Empty || invocationGroupId == Guid.Empty
            || !expected.Witnesses.Contains(testIdentity, StringComparer.Ordinal)
            || started < TimeSpan.Zero || ended < started || !Enum.IsDefined(status)
            || status == ConformanceWitnessStatus.NotApplicable)
        { throw new ArgumentException("EvidenceSchemaInvalid"); }
        ExecutionId = executionId;
        RunId = runId;
        InvocationGroupId = invocationGroupId;
        TestIdentity = testIdentity;
        BindingId = ConformanceBindingDeclaration.Id(expected.BindingId);
        MatrixId = ConformanceBindingDeclaration.Id(expected.MatrixId);
        PackageSha256 = Digest(packageSha256);
        AssemblySha256 = Digest(assemblySha256);
        InputSha256 = Digest(inputSha256);
        StartedMs = started.TotalMilliseconds;
        EndedMs = ended.TotalMilliseconds;
        Status = status;
        ProofSha256 = Digest(proofSha256);
    }

    public Guid ExecutionId { get; }
    public Guid RunId { get; }
    public Guid InvocationGroupId { get; }
    public string TestIdentity { get; }
    public string BindingId { get; }
    public string MatrixId { get; }
    public string PackageSha256 { get; }
    public string AssemblySha256 { get; }
    public string InputSha256 { get; }
    public double StartedMs { get; }
    public double EndedMs { get; }
    public ConformanceWitnessStatus Status { get; }
    public string ProofSha256 { get; }
    public override string ToString() => "ConformanceRuntimeWitness";

    private static string Digest(string value)
        => value is not null && DigestPattern().IsMatch(value) ? value : throw new ArgumentException("EvidenceSchemaInvalid");

    [GeneratedRegex(@"\A[0-9a-f]{64}\z", RegexOptions.CultureInvariant)]
    private static partial Regex DigestPattern();
}

public enum ConformanceWitnessStatus { Passed, Failed, NotApplicable, Incomplete }
