using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;

namespace Hoard.Artifacts.Tests;

internal sealed class ArtifactProviderDriver : IArtifactProviderDriver
{
    private readonly ArtifactTestRoot root;
    private readonly IArtifactStoreLifetime lifetime;
    private ArtifactProviderDriver(string providerId, ArtifactTestRoot root, IArtifactStoreLifetime lifetime,
        ArtifactStoreIdentity identity, ArtifactCoordinationAuthority authority,
        LocalFaultControls? local, ObjectFaultControls? objects)
    {
        ProviderId = providerId;
        this.root = root;
        this.lifetime = lifetime;
        Identity = identity;
        Authority = authority;
        Store = (IArtifactStore)lifetime;
        Validator = (IArtifactEvidenceValidator)lifetime;
        Maintenance = (IArtifactMaintenance)lifetime;
        LocalControls = local;
        ObjectControls = objects;
    }
    public string ProviderId { get; }
    public ArtifactStoreIdentity Identity { get; }
    public ArtifactCoordinationAuthority Authority { get; }
    public IArtifactStore Store { get; }
    public IArtifactEvidenceValidator Validator { get; }
    public IArtifactMaintenance Maintenance { get; }
    public LocalFaultControls? LocalControls { get; }
    public ObjectFaultControls? ObjectControls { get; }

    public static async Task<ArtifactProviderDriver> CreateAsync(string providerId, TimeProvider? clock = null,
        ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references = null)
    {
        if (providerId is not ("local" or "object")) { throw new ArgumentException("Unknown artifact fixture."); }
        var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{providerId}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity, clock, references);
        var local = providerId == "local" ? new LocalFaultControls() : null;
        var objects = providerId == "object" ? new ObjectFaultControls() : null;
        IArtifactStoreLifetime lifetime = providerId == "local"
            ? new LocalArtifactStore(root.Path, clock, local) : new ObjectArtifactStore(root.Path, clock, objects);
        var driver = new ArtifactProviderDriver(providerId, root, lifetime, identity, authority, local, objects);
        try
        {
            Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await lifetime.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), default));
            return driver;
        }
        catch
        {
            await driver.DisposeAsync();
            throw;
        }
    }

    public async ValueTask DisposeAsync()
    {
        var result = await lifetime.StopAsync(new(), default);
        if (result is not ArtifactResult<ArtifactShutdown>.Success released
            || released.Value.State != ArtifactCleanupState.Released)
        {
            root.AllowCleanup = false;
            throw new InvalidOperationException("Artifact fixture retains owned work; private root preserved.");
        }
        root.Dispose();
    }
}
