using System.Collections.Immutable;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Evidence;

public sealed class ConformanceArtifactRecoveryOrigin
{
    private readonly ConformanceSessionOrigin observation;

    internal ConformanceArtifactRecoveryOrigin(
        ConformanceSessionOrigin observation, Guid sourceSessionId, string recoveryInputSha256)
    {
        this.observation = observation;
        if (sourceSessionId == Guid.Empty || sourceSessionId == observation.SessionId)
        { throw new ArgumentException("BindingInvalid"); }
        SourceSessionId = sourceSessionId;
        RecoveryInputSha256 = ConformanceBindingDeclaration.Hash(recoveryInputSha256);
    }

    public int SchemaVersion => 1;
    public string Kind => "artifact-recovery";
    public Guid RunId => observation.RunId;
    public string CaseId => observation.CaseId;
    public Guid SessionId => observation.SessionId;
    public Guid SourceSessionId { get; }
    public string RecoveryInputSha256 { get; }
    public string FactoryOperation => "recover";
    public string DescriptorSha256 => observation.DescriptorSha256;
    public string RuntimeVersion => observation.RuntimeVersion;
    public string ProcessArchitecture => observation.ProcessArchitecture;
    public ImmutableSortedDictionary<string, ConformanceObservedComponent> Components => observation.Components;
    public override string ToString() => nameof(ConformanceArtifactRecoveryOrigin);
}
