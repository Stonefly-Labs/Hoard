using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Fixtures.Conformance.Bindings.Mutations;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Contributor;

public sealed class ForwardingMetadataBinding : IMetadataConformanceBinding
{
    private readonly MemoryBinding inner;
    private readonly bool injectStaleReplay;

    public ForwardingMetadataBinding(string providerPackageSha256, bool injectStaleReplay = false)
    {
        inner = new(providerPackageSha256);
        this.injectStaleReplay = injectStaleReplay;
        var source = inner.Declaration;
        Declaration = new("example.metadata.forwarding", source.Category, source.PackageId,
            source.PackageVersion, source.PackageSha256,
            [.. source.Capabilities, "forwarding-example"], source.Faults);
    }

    public ConformanceBindingDeclaration Declaration { get; }

    public async ValueTask<IMetadataConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        new Session(await inner.CreateSessionAsync(context, cancellationToken), injectStaleReplay);

    public async ValueTask<IMetadataConformanceSession> CreateLegacySessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        new Session(await inner.CreateLegacySessionAsync(context, cancellationToken), injectStaleReplay);

    private sealed class Session : IMetadataConformanceSession
    {
        private readonly IMetadataConformanceSession inner;
        private readonly bool injectStaleReplay;

        public Session(IMetadataConformanceSession inner, bool injectStaleReplay)
        {
            this.inner = inner;
            this.injectStaleReplay = injectStaleReplay;
            Store = new StaleOperationStore(inner.Store, injectStaleReplay);
        }

        public IMetadataStore Store { get; }
        public IMetadataSchemaAdministration Schema => inner.Schema;
        public IMetadataConformanceAuthority Authority => inner.Authority;
        public IMetadataConformanceFaultDriver Faults => inner.Faults;

        public async ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken) =>
            new Session(await inner.ReopenAsync(cancellationToken), injectStaleReplay);

        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
            inner.ObserveCleanupAsync(cancellationToken);

        public ValueTask DisposeAsync() => inner.DisposeAsync();
    }
}
