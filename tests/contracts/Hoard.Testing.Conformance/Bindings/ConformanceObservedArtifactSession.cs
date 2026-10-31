using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Testing.Conformance.Bindings;

public sealed class ConformanceObservedArtifactSession : IArtifactConformanceSession
{
    private readonly IArtifactConformanceSession session;
    private readonly ConformanceSessionOriginTracker origins;
    private readonly Guid sessionId = Guid.NewGuid();
    private readonly Guid? parentSessionId;
    private readonly Lazy<IArtifactStore> store;
    private readonly Lazy<IArtifactEvidenceValidator> validator;
    private readonly Lazy<IArtifactMaintenance> maintenance;
    private readonly Lazy<IArtifactStoreLifetime> lifetime;
    private readonly Lazy<IArtifactCoordinationAuthority> authority;
    private readonly Lazy<ArtifactStoreIdentity> identity;
    private readonly Lazy<IArtifactConformanceFaultDriver> faults;

    internal ConformanceObservedArtifactSession(IArtifactConformanceSession session,
        ConformanceSessionOriginTracker origins, Guid? parentSessionId)
    {
        this.session = session ?? throw new ArgumentException("BindingInvalid");
        this.origins = origins;
        this.parentSessionId = parentSessionId;
        // Defer provider getters until the caller owns the returned session for cleanup.
        store = new(() => session.Store ?? throw new ArgumentException("BindingInvalid"));
        validator = new(() => session.Validator ?? throw new ArgumentException("BindingInvalid"));
        maintenance = new(() => session.Maintenance ?? throw new ArgumentException("BindingInvalid"));
        lifetime = new(() => session.Lifetime ?? throw new ArgumentException("BindingInvalid"));
        authority = new(() => session.Authority ?? throw new ArgumentException("BindingInvalid"));
        identity = new(() => session.Identity ?? throw new ArgumentException("BindingInvalid"));
        faults = new(() => session.Faults ?? throw new ArgumentException("BindingInvalid"));
    }

    public IArtifactStore Store => store.Value;
    public IArtifactEvidenceValidator Validator => validator.Value;
    public IArtifactMaintenance Maintenance => maintenance.Value;
    public IArtifactStoreLifetime Lifetime => lifetime.Value;
    public IArtifactCoordinationAuthority Authority => authority.Value;
    public ArtifactStoreIdentity Identity => identity.Value;
    public IArtifactConformanceFaultDriver Faults => faults.Value;

    public static async ValueTask<ConformanceObservedArtifactSession> OpenAsync(
        IArtifactConformanceBinding binding, ConformanceRunContext context, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(binding);
        ArgumentNullException.ThrowIfNull(context);
        cancellationToken.ThrowIfCancellationRequested();
        var declaration = binding.Declaration;
        ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Artifacts);
        var origins = new ConformanceSessionOriginTracker(binding, context, declaration);
        var session = await binding.CreateSessionAsync(context, cancellationToken).ConfigureAwait(false);
        return new(session, origins, null);
    }

    public ConformanceSessionOrigin CaptureOrigin()
    {
        origins.ValidateFaults(Faults.SupportedFaults);
        return origins.Capture(session, sessionId, parentSessionId,
            ("store", Store), ("validator", Validator), ("maintenance", Maintenance),
            ("lifetime", Lifetime), ("authority", Authority), ("faults", Faults));
    }

    public async ValueTask<IArtifactConformanceSession> ReopenAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var reopened = await session.ReopenAsync(cancellationToken).ConfigureAwait(false);
        return new ConformanceObservedArtifactSession(reopened, origins, sessionId);
    }

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
        session.ObserveCleanupAsync(cancellationToken);

    public ValueTask DisposeAsync() => session.DisposeAsync();
}
