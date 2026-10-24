using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Testing.Conformance.Bindings;

public sealed class ConformanceObservedMetadataSession : IMetadataConformanceSession
{
    private readonly IMetadataConformanceSession session;
    private readonly ConformanceSessionOriginTracker origins;
    private readonly Guid sessionId = Guid.NewGuid();
    private readonly Guid? parentSessionId;
    private readonly Lazy<IMetadataStore> store;
    private readonly Lazy<IMetadataSchemaAdministration> schema;
    private readonly Lazy<IMetadataConformanceAuthority> authority;
    private readonly Lazy<IMetadataConformanceFaultDriver> faults;

    private ConformanceObservedMetadataSession(IMetadataConformanceSession session,
        ConformanceSessionOriginTracker origins, Guid? parentSessionId)
    {
        this.session = session ?? throw new ArgumentException("BindingInvalid");
        this.origins = origins;
        this.parentSessionId = parentSessionId;
        // Defer provider getters until the caller owns the returned session for cleanup.
        store = new(() => session.Store ?? throw new ArgumentException("BindingInvalid"));
        schema = new(() => session.Schema ?? throw new ArgumentException("BindingInvalid"));
        authority = new(() => session.Authority ?? throw new ArgumentException("BindingInvalid"));
        faults = new(() => session.Faults ?? throw new ArgumentException("BindingInvalid"));
    }

    public IMetadataStore Store => store.Value;
    public IMetadataSchemaAdministration Schema => schema.Value;
    public IMetadataConformanceAuthority Authority => authority.Value;
    public IMetadataConformanceFaultDriver Faults => faults.Value;

    public static ValueTask<ConformanceObservedMetadataSession> OpenAsync(
        IMetadataConformanceBinding binding, ConformanceRunContext context, CancellationToken cancellationToken) =>
        OpenCoreAsync(binding, context, cancellationToken, false);

    public static ValueTask<ConformanceObservedMetadataSession> OpenLegacyAsync(
        IMetadataConformanceBinding binding, ConformanceRunContext context, CancellationToken cancellationToken) =>
        OpenCoreAsync(binding, context, cancellationToken, true);

    private static async ValueTask<ConformanceObservedMetadataSession> OpenCoreAsync(
        IMetadataConformanceBinding binding, ConformanceRunContext context, CancellationToken cancellationToken, bool legacy)
    {
        ArgumentNullException.ThrowIfNull(binding);
        ArgumentNullException.ThrowIfNull(context);
        cancellationToken.ThrowIfCancellationRequested();
        var declaration = binding.Declaration;
        ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata);
        var origins = new ConformanceSessionOriginTracker(binding, context, declaration);
        var session = await (legacy ? binding.CreateLegacySessionAsync(context, cancellationToken)
            : binding.CreateSessionAsync(context, cancellationToken)).ConfigureAwait(false);
        return new(session, origins, null);
    }

    public ConformanceSessionOrigin CaptureOrigin()
    {
        origins.ValidateFaults(Faults.SupportedFaults);
        return origins.Capture(session, sessionId, parentSessionId,
            ("store", Store), ("schema", Schema), ("authority", Authority), ("faults", Faults));
    }

    public async ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var reopened = await session.ReopenAsync(cancellationToken).ConfigureAwait(false);
        return new ConformanceObservedMetadataSession(reopened, origins, sessionId);
    }

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
        session.ObserveCleanupAsync(cancellationToken);

    public ValueTask DisposeAsync() => session.DisposeAsync();
}
