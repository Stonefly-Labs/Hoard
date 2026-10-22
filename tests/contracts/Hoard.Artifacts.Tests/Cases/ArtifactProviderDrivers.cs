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
    public ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions options)
        => lifetime.StopAsync(options, default);
    public Task WhenIdleAsync() => lifetime switch
    {
        LocalArtifactStore local => local.WhenIdleForQualificationAsync(),
        ObjectArtifactStore objects => objects.WhenIdleForQualificationAsync(),
        _ => throw new InvalidOperationException("Unknown artifact fixture.")
    };

    public void DamageOnlyPayload(bool truncate)
    {
        var directory = System.IO.Path.Combine(root.Path, ProviderId == "local" ? "data" : "objects");
        var path = Directory.EnumerateFiles(directory).Single();
        using var file = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
        if (truncate) { file.SetLength(file.Length - 1); }
        else { file.WriteByte(0xff); }
        file.Flush(flushToDisk: true);
    }

    public static async Task<ArtifactProviderDriver> CreateAsync(string providerId, TimeProvider? clock = null,
        ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references = null,
        Func<ArtifactCoordinationAuthority, IArtifactCoordinationAuthority>? decorate = null)
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
            var admission = await lifetime.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, decorate?.Invoke(authority) ?? authority, limits), new(), default);
            Assert.True(admission is ArtifactResult<ArtifactAdmission>.Success,
                admission is ArtifactResult<ArtifactAdmission>.Failure failure
                    ? $"Artifact initialization failed ({failure.Code}, {local?.InitializationFailure})." : "Unexpected artifact admission result.");
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
