using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Local;

public sealed class LocalBinding : IArtifactRecoveryConformanceBinding
{
    private readonly ArtifactAssertionOptions options;

    public LocalBinding(string providerPackageSha256, string providerPackageVersion = "0.1.0",
        ArtifactAssertionOptions? options = null)
    {
        this.options = options ?? new();
        Declaration = new("fixture.artifact.local", ConformanceCategory.Artifacts,
            "Hoard.Fixtures.Artifacts.Local", providerPackageVersion, providerPackageSha256,
            ["artifacts", "durable-local-process-crash"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts));
    }

    public ConformanceBindingDeclaration Declaration { get; }

    public async ValueTask<IArtifactConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        new ArtifactConformanceSession(
            await LocalArtifactAssertionSessions.CreateAsync(context, options, cancellationToken), context);

    public async ValueTask<IArtifactConformanceSession> ReopenSessionAsync(
        ConformanceRunContext context, ArtifactStoreIdentity identity, CancellationToken cancellationToken) =>
        new ArtifactConformanceSession(
            await LocalArtifactAssertionSessions.ReopenAsync(context, options, identity, cancellationToken), context);
}
