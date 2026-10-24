using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Memory;

public sealed class MemoryBinding : IMetadataConformanceBinding
{
    public MemoryBinding(string providerPackageSha256, string providerPackageVersion = "0.1.0")
    {
        Declaration = new("fixture.metadata.memory", ConformanceCategory.Metadata,
            "Hoard.Fixtures.Metadata.Memory", providerPackageVersion, providerPackageSha256,
            ["metadata", "non-durable", "logical-schema-upgrade"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
    }

    public ConformanceBindingDeclaration Declaration { get; }

    public ValueTask<IMetadataConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, new FixturePublicationAuthority(), null, 2, cancellationToken);

    public ValueTask<IMetadataConformanceSession> CreateLegacySessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, new FixturePublicationAuthority(), null, 1, cancellationToken);

    private static async ValueTask<IMetadataConformanceSession> CreateAsync(
        ConformanceRunContext context, FixturePublicationAuthority authority,
        MemoryFixtureImage? image, int compatibleSchema, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(context);
        var resource = await context.Resources.AllocateDirectoryAsync(cancellationToken);
        return new Session(context, resource, authority, image, compatibleSchema);
    }

    private sealed class Session : IMetadataConformanceSession
    {
        private readonly object gate = new();
        private readonly SemaphoreSlim reopening = new(1, 1);
        private readonly ConformanceRunContext context;
        private readonly ConformanceOwnedDirectory resource;
        private readonly FixturePublicationAuthority authority;
        private readonly MemoryMetadataStore store;
        private readonly MemoryMetadataFaults faults;
        private Task? disposal;
        private Task? settlement;
        private Task<ConformanceCleanupObservation>? cleanup;
        private MemoryFixtureImage? reopenImage;
        private bool reopened;

        public Session(ConformanceRunContext context, ConformanceOwnedDirectory resource,
            FixturePublicationAuthority authority, MemoryFixtureImage? image, int compatibleSchema)
        {
            this.context = context;
            this.resource = resource;
            this.authority = authority;
            faults = new(context, IsClosing);
            store = new(authority, context.Clock, faults.OnBoundaryAsync, faults.OnDiagnostic,
                compatibleSchema: compatibleSchema, logicalImage: image);
            faults.Attach(store);
        }

        public IMetadataStore Store => store;
        public IMetadataSchemaAdministration Schema => store;
        public IMetadataConformanceAuthority Authority => authority;
        public IMetadataConformanceFaultDriver Faults => faults;

        private bool IsClosing()
        {
            lock (gate) { return settlement is not null; }
        }

        public async ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken)
        {
            if (!await reopening.WaitAsync(context.ControlBudget, cancellationToken))
            { throw new InvalidOperationException("BindingInvalid"); }
            try
            {
                if (reopened) { throw new InvalidOperationException("BindingInvalid"); }
                if (reopenImage is null)
                {
                    await faults.AwaitSettlementAsync(cancellationToken);
                    lock (gate)
                    {
                        if (disposal is not null) { throw new InvalidOperationException("BindingInvalid"); }
                        reopenImage = store.CloseAndCaptureLogicalImageForTest();
                    }
                }
                await DisposeAsync();
                var current = await CreateAsync(context, authority, reopenImage, 2, cancellationToken);
                reopened = true;
                return current;
            }
            finally { reopening.Release(); }
        }

        public ValueTask DisposeAsync()
        {
            lock (gate)
            {
                if (disposal is null || disposal.IsFaulted || disposal.IsCanceled)
                {
                    var disposing = store.DisposeAsync().AsTask();
                    settlement ??= store.ObserveWorkSettlementForTest();
                    cleanup = context.Resources.ReleaseAsync(resource, settlement, CancellationToken.None).AsTask();
                    disposal = DisposeCoreAsync(disposing, cleanup);
                }
                return new(disposal);
            }
        }

        private async Task DisposeCoreAsync(Task disposing, Task<ConformanceCleanupObservation> observing)
        {
            await Task.WhenAll(disposing, observing);
            if ((await observing).State != ConformanceOwnershipState.Settling)
            { throw new InvalidOperationException("Memory metadata cleanup incomplete; live work remains owned."); }
            await faults.DisposeControlsAsync();
        }

        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            lock (gate)
            {
                if (cleanup is { IsCompleted: true }) { return new(cleanup); }
                return ValueTask.FromResult(new ConformanceCleanupObservation(
                    settlement is null ? ConformanceOwnershipState.Active : ConformanceOwnershipState.Settling,
                    [resource.ResourceId]));
            }
        }
    }
}
