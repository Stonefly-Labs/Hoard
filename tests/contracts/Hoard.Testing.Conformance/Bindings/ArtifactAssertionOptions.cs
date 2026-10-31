using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Bindings;

public enum ArtifactAdmissionProbe
{
    None, Complete, Version, Publication, Deletion, Recovery, Fencing, Readers, Streaming, ForeignAuthority
}

public sealed class ArtifactAssertionOptions
{
    public ArtifactAssertionOptions(ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? references = null)
        : this(ArtifactAdmissionProbe.None, limits, references) { }

    public ArtifactAssertionOptions(ArtifactAdmissionProbe admissionProbe, ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? references = null)
    {
        if (!Enum.IsDefined(admissionProbe)) { throw new ArgumentException("BindingInvalid"); }
        Limits = limits ?? new();
        References = references;
        AdmissionProbe = admissionProbe;
    }

    public ArtifactLimits Limits { get; }
    public Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? References { get; }
    public ArtifactAdmissionProbe AdmissionProbe { get; }
}

public sealed record ArtifactReferenceObservation
{
    public ArtifactReferenceObservation(bool available, long liveReferences, Guid revision)
    {
        if (liveReferences < 0 || available && revision == Guid.Empty || !available && liveReferences != 0)
        { throw new ArgumentException("BindingInvalid"); }
        Available = available;
        LiveReferences = liveReferences;
        Revision = revision;
    }

    public bool Available { get; }
    public long LiveReferences { get; }
    public Guid Revision { get; }
}
