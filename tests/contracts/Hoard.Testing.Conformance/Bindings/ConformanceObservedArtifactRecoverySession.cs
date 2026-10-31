using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Testing.Conformance.Bindings;

public sealed class ConformanceObservedArtifactRecoverySession : IArtifactConformanceSession
{
    private readonly IArtifactConformanceSession session;
    private readonly ConformanceObservedArtifactSession observed;
    private readonly Guid sourceSessionId;
    private readonly string recoveryInputSha256;

    private ConformanceObservedArtifactRecoverySession(
        IArtifactConformanceSession session, ConformanceSessionOriginTracker origins,
        Guid sourceSessionId, string recoveryInputSha256)
    {
        this.session = session;
        observed = new(session, origins, null);
        this.sourceSessionId = sourceSessionId;
        this.recoveryInputSha256 = recoveryInputSha256;
    }

    public IArtifactStore Store => observed.Store;
    public IArtifactEvidenceValidator Validator => observed.Validator;
    public IArtifactMaintenance Maintenance => observed.Maintenance;
    public IArtifactStoreLifetime Lifetime => observed.Lifetime;
    public IArtifactCoordinationAuthority Authority => observed.Authority;
    public ArtifactStoreIdentity Identity => observed.Identity;
    public IArtifactConformanceFaultDriver Faults => observed.Faults;

    public static async ValueTask<ConformanceObservedArtifactRecoverySession> OpenAsync(
        IArtifactRecoveryConformanceBinding binding, ConformanceRunContext context, ArtifactStoreIdentity identity,
        Guid sourceSessionId, string recoveryInputSha256, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(binding);
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(identity);
        if (sourceSessionId == Guid.Empty) { throw new ArgumentException("BindingInvalid"); }
        recoveryInputSha256 = ConformanceBindingDeclaration.Hash(recoveryInputSha256);
        cancellationToken.ThrowIfCancellationRequested();
        var declaration = binding.Declaration;
        ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Artifacts);
        if (!declaration.Capabilities.Contains("durable-local-process-crash", StringComparer.Ordinal))
        { throw new ArgumentException("BindingInvalid"); }
        var origins = new ConformanceSessionOriginTracker(binding, context, declaration);
        var session = await binding.ReopenSessionAsync(context, identity, cancellationToken).ConfigureAwait(false);
        return new(session, origins, sourceSessionId, recoveryInputSha256);
    }

    public ConformanceArtifactRecoveryOrigin CaptureOrigin() =>
        new(observed.CaptureOrigin(), sourceSessionId, recoveryInputSha256);

    public ValueTask<IArtifactConformanceSession> ReopenAsync(CancellationToken cancellationToken) =>
        session.ReopenAsync(cancellationToken);

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
        observed.ObserveCleanupAsync(cancellationToken);

    public ValueTask DisposeAsync() => observed.DisposeAsync();
}
