using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Fixtures.Metadata.Sqlite;

namespace Hoard.Fixtures.Metadata.Hosting;

public sealed class MetadataFixtureSession : IAsyncDisposable
{
    private string? ownedDirectory;
    private readonly TimeProvider clock;
    private MetadataFixtureSession(string provider, TimeProvider clock, string? databasePath, int initialSchema, string compatibleSchema,
        MemoryFixtureImage? logicalImage = null)
    {
        this.clock = clock;
        Controls = new();
        Authority = new(Controls);
        Provider = provider;
        switch (provider)
        {
            case "sqlite":
                if (databasePath is null)
                {
                    var parent = Environment.GetEnvironmentVariable("HOARD_METADATA_WORKSPACE") ?? Path.GetTempPath();
                    ownedDirectory = Path.Combine(parent, "hoard-metadata-case-" + Guid.NewGuid().ToString("N"));
                    Directory.CreateDirectory(ownedDirectory);
                    if (!OperatingSystem.IsWindows())
                    { File.SetUnixFileMode(ownedDirectory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
                    databasePath = Path.Combine(ownedDirectory, "metadata.db");
                }
                DatabasePath = Path.GetFullPath(databasePath);
                var sqlite = new SqliteMetadataStore(DatabasePath, Authority, clock, Controls.ObserveAsync, Controls.Diagnose, compatibleSchema);
                Store = sqlite;
                Schema = sqlite;
                break;
            case "memory":
                var memory = new MemoryMetadataStore(Authority, clock, Controls.ObserveAsync, Controls.Diagnose, initialSchema,
                    compatibleSchema.EndsWith("-v1", StringComparison.Ordinal) ? 1 : 2, logicalImage);
                Store = memory;
                Schema = memory;
                break;
            default: throw new ArgumentException("Unknown metadata fixture selection.");
        }
    }

    public string Provider { get; }
    public string? DatabasePath { get; }
    public IMetadataStore Store { get; }
    public IMetadataSchemaAdministration Schema { get; }
    public MetadataFixtureControls Controls { get; }
    public ControlledPublicationAuthority Authority { get; }

    public IAsyncDisposable ObserveBeforeSchemaUpgrade(Func<ValueTask> observer) =>
        Controls.RegisterObserver(Store switch
        {
            SqliteMetadataStore => "U0",
            MemoryMetadataStore => "memory.upgrade.before_decision",
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        }, observer);

    public IAsyncDisposable ObserveSchemaCandidatePrepared(Func<ValueTask> observer) =>
        Controls.RegisterObserver(Store switch
        {
            SqliteMetadataStore => "U1",
            MemoryMetadataStore => "memory.upgrade.before_decision",
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        }, observer);

    public MetadataContinuation CorruptContinuationForTest(
        MetadataContinuation continuation, string component, string shape) => Store switch
        {
            SqliteMetadataStore => SqlitePayloadDamage.Continuation(continuation, component switch
            {
                "ContractVersion" => "ContractVersion",
                "Epoch" => "Epoch",
                "Schema" => "Schema",
                "Query" => "Query",
                "PageSize" => "PageSize",
                "Position" => "LastKey",
                _ => throw new ArgumentException("Unknown continuation component.", nameof(component))
            }, shape),
            MemoryMetadataStore => MemoryPayloadDamage.Continuation(continuation, component switch
            {
                "ContractVersion" => "Contract",
                "Epoch" or "Schema" => "Epoch",
                "Query" => "Query",
                "PageSize" => "Size",
                "Position" => "After",
                _ => throw new ArgumentException("Unknown continuation component.", nameof(component))
            }, shape),
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        };

    public static MetadataFixtureSession Create(string provider, TimeProvider clock, string? databasePath = null,
        int initialSchema = 0, string compatibleSchema = "fixture-sqlite-v2") =>
        new(provider, clock, databasePath, initialSchema, compatibleSchema);

    public static MetadataFixtureSession CreateFromEnvironment(TimeProvider clock) =>
        Create(Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")
            ?? throw new InvalidOperationException("Metadata acceptance requires an explicit provider."), clock);

    public Task WhenIdleAsync() => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.WhenIdleAsync(),
        MemoryMetadataStore memory => memory.WhenIdleAsync(),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public async ValueTask<MetadataFixtureSession> ReopenAsync(string compatibleSchema = "fixture-sqlite-v2")
    {
        await WhenIdleAsync();
        var image = Store is MemoryMetadataStore memory ? memory.CaptureLogicalImage() : null;
        await Store.DisposeAsync();
        var reopened = new MetadataFixtureSession(Provider, clock, DatabasePath, 0, compatibleSchema, image)
        { ownedDirectory = ownedDirectory };
        ownedDirectory = null;
        return reopened;
    }

    public async ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync()
    {
        if (Store is MemoryMetadataStore memory) { return memory.AuthorizeLogicalUpgrade(); }
        var result = await ((SqliteMetadataStore)Store).CaptureRecoveryPointAsync(new(), default);
        return result is MetadataResult<MetadataRecoveryPoint>.Success success ? success.Value
            : throw new InvalidOperationException("Fixture recovery authorization failed.");
    }

    public ValueTask<MetadataResult<MetadataId>> FillLedgerForTestAsync() => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.FillLedgerForTestAsync(),
        MemoryMetadataStore memory => memory.FillLedgerForTestAsync(),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public ValueTask<MetadataResult<MetadataId>> CorruptRecordForTestAsync(MetadataSelector selector) => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.CorruptRecordForTestAsync(selector),
        MemoryMetadataStore memory => memory.CorruptRecordForTestAsync(selector),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public ValueTask<MetadataResult<MetadataId>> MakeFutureSchemaForTestAsync() => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.MakeFutureSchemaForTestAsync(),
        MemoryMetadataStore memory => memory.MakeFutureSchemaForTestAsync(),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotAsync(MetadataReadGroup request) =>
        ObserveIndependentSnapshotAsync(request, default);

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotAsync(
        MetadataReadGroup request, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store is SqliteMetadataStore sqlite
            ? ValueTask.FromResult<MetadataResult<MetadataReadSnapshot>>(new MetadataResult<MetadataReadSnapshot>.Success(sqlite.ObserveCommittedSnapshot(request)))
            : Store.ReadAsync(request, new(), cancellationToken);
    }

    public ValueTask<IDisposable> HoldWriterForTestAsync() => HoldWriterForTestAsync(default);

    public ValueTask<IDisposable> HoldWriterForTestAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store switch
        {
            SqliteMetadataStore sqlite => ValueTask.FromResult(sqlite.HoldIndependentWriterForTest()),
            MemoryMetadataStore memory => memory.HoldWriterForTestAsync(cancellationToken),
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        };
    }

    public ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationForTestAsync(CanonicalText resource, long generation) => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.SetLeaseGenerationForTestAsync(resource, generation),
        MemoryMetadataStore memory => memory.SetLeaseGenerationForTestAsync(resource, generation),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public void InjectStorageCapacityForTest()
    {
        switch (Store)
        {
            case SqliteMetadataStore sqlite: sqlite.InjectStorageCapacityForTest(); break;
            case MemoryMetadataStore memory: memory.InjectStorageCapacityForTest(); break;
            default: throw new InvalidOperationException("Unknown metadata fixture.");
        }
    }

    public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutForTestAsync(bool partial) => Store switch
    {
        SqliteMetadataStore sqlite => sqlite.CreateUnrecognizedLayoutForTestAsync(partial),
        MemoryMetadataStore memory => memory.CreateUnrecognizedLayoutForTestAsync(partial),
        _ => throw new InvalidOperationException("Unknown metadata fixture.")
    };

    public async ValueTask DisposeAsync()
    {
        await Store.DisposeAsync();
        if (ownedDirectory is not null && Directory.Exists(ownedDirectory)) { Directory.Delete(ownedDirectory, recursive: true); }
    }
}
