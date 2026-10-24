using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Bindings;

public sealed class ArtifactAssertionOptions
{
    public ArtifactAssertionOptions(ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? references = null)
    {
        Limits = limits ?? new();
        References = references;
    }

    public ArtifactLimits Limits { get; }
    public Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? References { get; }
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
