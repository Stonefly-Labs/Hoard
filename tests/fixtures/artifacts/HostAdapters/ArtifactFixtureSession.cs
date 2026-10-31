using Hoard.Abstractions.Storage;
using System.Diagnostics;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed record ArtifactFixtureAdmissionProfile
{
    public ArtifactInitializationMode Mode { get; init; } = ArtifactInitializationMode.CreateEmpty;
    public ArtifactStoreIdentity? Store { get; init; }
    public Func<ArtifactCapabilities, ArtifactCapabilities>? CapabilitiesForAdmission { get; init; }
}

public sealed class ArtifactFixtureSession : IAsyncDisposable
{
    private readonly IArtifactStoreLifetime lifetime;
    private ArtifactFixtureSession(IArtifactStoreLifetime lifetime, ArtifactStoreIdentity identity,
        ArtifactCoordinationAuthority authority, object controls)
    {
        this.lifetime = lifetime;
        Identity = identity;
        Authority = authority;
        Controls = controls;
        Store = (IArtifactStore)lifetime;
        Validator = (IArtifactEvidenceValidator)lifetime;
        Maintenance = (IArtifactMaintenance)lifetime;
    }

    public ArtifactStoreIdentity Identity { get; }
    public ArtifactCoordinationAuthority Authority { get; }
    public object Controls { get; }
    public IArtifactStore Store { get; }
    public IArtifactEvidenceValidator Validator { get; }
    public IArtifactMaintenance Maintenance { get; }
    public ArtifactCapabilities Capabilities => Store.Capabilities;
    public bool Ready => !Authority.HasRetainedWork && lifetime switch
    {
        LocalArtifactStore local => local.Ready,
        ObjectArtifactStore objects => objects.Ready,
        _ => throw new InvalidOperationException("Unknown artifact fixture.")
    };
    public Task WhenIdleForQualificationAsync() => lifetime switch
    {
        LocalArtifactStore local => local.WhenIdleForQualificationAsync(),
        ObjectArtifactStore objects => objects.WhenIdleForQualificationAsync(),
        _ => throw new InvalidOperationException("Unknown artifact fixture.")
    };

    public static Task<ArtifactFixtureSession> CreateForQualificationAsync(string provider, string root,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references = null,
        ArtifactLimits? limits = null, CancellationToken cancellationToken = default)
        => CreateForQualificationAsync(provider, root, references, limits, cancellationToken, null);

    public static async Task<ArtifactFixtureSession> CreateForQualificationAsync(string provider, string root,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references,
        ArtifactLimits? limits, CancellationToken cancellationToken, ArtifactFixtureAdmissionProfile? profile)
    {
        if (provider is not ("local" or "object")) { throw new ArgumentException("Unknown artifact fixture selection."); }
        var identity = profile?.Store ?? new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        if (identity.ProviderModuleId != $"fixture.artifact.{provider}"
            || profile is { Mode: ArtifactInitializationMode.ReopenCompatible, Store: null })
        { throw new ArgumentException("Artifact fixture reopen requires its exact selected store identity."); }
        var authority = new ArtifactCoordinationAuthority(identity, references: references);
        var local = provider == "local" ? new LocalFaultControls { CapabilitiesForAdmission = profile?.CapabilitiesForAdmission } : null;
        var objects = provider == "object" ? new ObjectFaultControls { CapabilitiesForAdmission = profile?.CapabilitiesForAdmission } : null;
        IArtifactStoreLifetime lifetime = provider == "local"
            ? new LocalArtifactStore(root, controls: local)
            : new ObjectArtifactStore(root, controls: objects);
        var session = new ArtifactFixtureSession(lifetime, identity, authority,
            local is { } controls ? controls : (object)objects!);
        var result = await lifetime.InitializeAsync(new(profile?.Mode ?? ArtifactInitializationMode.CreateEmpty,
            identity, authority, limits), new(), cancellationToken);
        if (result is ArtifactResult<ArtifactAdmission>.Success) { return session; }
        var stopped = await lifetime.StopAsync(new(), default);
        if (stopped is not ArtifactResult<ArtifactShutdown>.Success)
        { throw new InvalidOperationException("Artifact fixture admission failed with retained ownership."); }
        var code = result is ArtifactResult<ArtifactAdmission>.Failure failed ? failed.Code : ArtifactFailureCode.InternalFailure;
        throw new InvalidOperationException($"Artifact fixture admission failed ({code}).");
    }

    public async ValueTask DisposeAsync()
    {
        var started = Stopwatch.GetTimestamp();
        var budget = TimeSpan.FromSeconds(5);
        if (!await Authority.DrainRetainedAsync(budget))
        { throw new InvalidOperationException("Artifact fixture shutdown retains authority ownership."); }
        var remaining = budget - Stopwatch.GetElapsedTime(started);
        if (remaining < TimeSpan.FromMilliseconds(1))
        { throw new InvalidOperationException("Artifact fixture shutdown exhausted its cleanup budget."); }
        var result = await lifetime.StopAsync(new(remaining), default);
        if (result is not ArtifactResult<ArtifactShutdown>.Success success || success.Value.State != ArtifactCleanupState.Released)
        { throw new InvalidOperationException("Artifact fixture shutdown retains live ownership."); }
    }
}
