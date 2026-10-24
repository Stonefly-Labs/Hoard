using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Sqlite;

public sealed class SqliteBinding : IMetadataConformanceBinding
{
    public SqliteBinding(string providerPackageSha256, string providerPackageVersion = "0.1.0")
    {
        Declaration = new("fixture.metadata.sqlite", ConformanceCategory.Metadata,
            "Hoard.Fixtures.Metadata.Sqlite", providerPackageVersion, providerPackageSha256,
            ["metadata", "durable", "schema-upgrade", "backup-recovery"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
    }

    public ConformanceBindingDeclaration Declaration { get; }

    public ValueTask<IMetadataConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, "fixture-sqlite-v2", cancellationToken);

    public ValueTask<IMetadataConformanceSession> CreateLegacySessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken) =>
        CreateAsync(context, "fixture-sqlite-v1", cancellationToken);

    private static async ValueTask<IMetadataConformanceSession> CreateAsync(
        ConformanceRunContext context, string compatibleSchema, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(context);
        var resource = await context.Resources.AllocateDirectoryAsync(cancellationToken);
        var ownership = new Ownership(context, resource);
        var session = new Session(ownership, compatibleSchema);
        ownership.Current = session;
        return session;
    }

    private sealed class Ownership(ConformanceRunContext context, ConformanceOwnedDirectory resource)
    {
        public ConformanceRunContext Context { get; } = context;
        public ConformanceOwnedDirectory Resource { get; } = resource;
        public FixturePublicationAuthority Authority { get; } = new();
        public SemaphoreSlim Transfer { get; } = new(1, 1);
        public Session? Current { get; set; }
        public bool Closing { get; set; }
        public Task? Settlement { get; set; }
        public Task? Disposal { get; set; }
        public Task<ConformanceCleanupObservation>? Cleanup { get; set; }
    }

    private sealed class Session : IMetadataConformanceSession
    {
        private readonly Ownership ownership;
        private readonly SqliteMetadataStore store;
        private readonly SqliteMetadataFaults faults;
        private Task? storeDisposal;
        private int closing;

        public Session(Ownership ownership, string compatibleSchema)
        {
            this.ownership = ownership;
            faults = new(ownership.Context, () => Volatile.Read(ref closing) != 0);
            store = new(Path.Combine(ownership.Resource.DirectoryPath, "metadata.db"),
                ownership.Authority, ownership.Context.Clock, faults.OnBoundaryAsync, faults.OnDiagnostic, compatibleSchema);
            faults.Attach(store);
        }

        public IMetadataStore Store => store;
        public IMetadataSchemaAdministration Schema => store;
        public IMetadataConformanceAuthority Authority => ownership.Authority;
        public IMetadataConformanceFaultDriver Faults => faults;

        public async ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken)
        {
            if (!await ownership.Transfer.WaitAsync(ownership.Context.ControlBudget, cancellationToken))
            { throw new InvalidOperationException("BindingInvalid"); }
            try
            {
                if (ownership.Closing || !ReferenceEquals(ownership.Current, this))
                { throw new InvalidOperationException("BindingInvalid"); }
                Volatile.Write(ref closing, 1);
                await CloseStore().WaitAsync(ownership.Context.ControlBudget, cancellationToken);
                await faults.DisposeControlsAsync();
                cancellationToken.ThrowIfCancellationRequested();
                var current = new Session(ownership, "fixture-sqlite-v2");
                ownership.Current = current;
                return current;
            }
            finally { ownership.Transfer.Release(); }
        }

        public async ValueTask DisposeAsync()
        {
            Task disposal;
            if (!await ownership.Transfer.WaitAsync(ownership.Context.ControlBudget))
            { throw new InvalidOperationException("CleanupIncomplete"); }
            try
            {
                if (!ReferenceEquals(ownership.Current, this)) { return; }
                if (ownership.Disposal is null || ownership.Disposal.IsFaulted || ownership.Disposal.IsCanceled)
                {
                    ownership.Closing = true;
                    Volatile.Write(ref closing, 1);
                    var disposing = CloseStore();
                    ownership.Settlement ??= store.ObserveLifetimeSettlementForTest();
                    ownership.Cleanup = ownership.Context.Resources.ReleaseAsync(
                        ownership.Resource, ownership.Settlement, CancellationToken.None).AsTask();
                    ownership.Disposal = DisposeCoreAsync(disposing, ownership.Cleanup);
                }
                disposal = ownership.Disposal;
            }
            finally { ownership.Transfer.Release(); }
            await disposal;
        }

        private Task CloseStore()
        {
            if (storeDisposal is null || storeDisposal.IsFaulted || storeDisposal.IsCanceled)
            {
                if (storeDisposal is { IsFaulted: true }) { _ = storeDisposal.Exception; }
                storeDisposal = store.DisposeAsync().AsTask();
            }
            return storeDisposal;
        }

        private async Task DisposeCoreAsync(Task disposing, Task<ConformanceCleanupObservation> observing)
        {
            await Task.WhenAll(disposing, observing);
            if ((await observing).State != ConformanceOwnershipState.Settling)
            { throw new InvalidOperationException("CleanupIncomplete"); }
            await faults.DisposeControlsAsync();
        }

        public async ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken)
        {
            await ownership.Transfer.WaitAsync(cancellationToken);
            try
            {
                if (ownership.Cleanup is { IsCompleted: true }) { return await ownership.Cleanup; }
                return new(ownership.Closing ? ConformanceOwnershipState.Settling : ConformanceOwnershipState.Active,
                    [ownership.Resource.ResourceId]);
            }
            finally { ownership.Transfer.Release(); }
        }
    }
}
