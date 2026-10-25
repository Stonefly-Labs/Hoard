using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;

public sealed class ObjectSemanticsBinding : IArtifactConformanceBinding
{
    private readonly ArtifactAssertionOptions options;

    public ObjectSemanticsBinding(string providerPackageSha256, string providerPackageVersion = "0.1.0",
        ArtifactAssertionOptions? options = null)
    {
        this.options = options ?? new();
        Declaration = new("fixture.artifact.object", ConformanceCategory.Artifacts,
            "Hoard.Fixtures.Artifacts.ObjectSemantics", providerPackageVersion, providerPackageSha256,
            ["artifacts", "non-durable-simulation"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts));
    }

    public ConformanceBindingDeclaration Declaration { get; }

    public async ValueTask<IArtifactConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        new ArtifactConformanceSession(
            await ObjectArtifactAssertionSessions.CreateAsync(context, options, cancellationToken), context);
}
