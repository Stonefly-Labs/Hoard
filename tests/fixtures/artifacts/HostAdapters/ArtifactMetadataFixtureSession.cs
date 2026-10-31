using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Fixtures.Metadata.Sqlite;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed class ArtifactMetadataFixtureSession : IAsyncDisposable
{
    private readonly object shutdownSync = new();
    private Task? shutdown;
    private ArtifactMetadataFixtureSession(ArtifactFixtureSession artifacts, IMetadataStore metadata,
        ArtifactMetadataPublicationAuthority publication, MetadataFixtureControls controls)
    {
        Artifacts = artifacts;
        Metadata = metadata;
        Publication = publication;
        Controls = controls;
    }
    public ArtifactFixtureSession Artifacts { get; }
    public IMetadataStore Metadata { get; }
    public ArtifactMetadataPublicationAuthority Publication { get; }
    public MetadataFixtureControls Controls { get; }

    public static async Task<ArtifactMetadataFixtureSession> CreateForQualificationAsync(
        string provider, string metadataProvider, string root)
    {
        if (provider is not ("local" or "object") || metadataProvider is not ("sqlite" or "memory"))
        { throw new ArgumentException("Unknown artifact/metadata fixture composition."); }
        IMetadataStore? metadata = null;
        var artifacts = await ArtifactFixtureSession.CreateForQualificationAsync(provider, Path.Combine(root, "artifacts"),
            async (stamp, token) =>
            {
                if (metadata is null) { return new(false, 0, Guid.Empty); }
                var result = await metadata.ReadAsync(new([new MetadataSelector.Artifact(stamp.Identity.Digest)]), new(), token);
                if (result is not MetadataResult<MetadataReadSnapshot>.Success read)
                { return new(false, 0, Guid.Empty); }
                return read.Value.Items[0] switch
                {
                    MetadataReadItem.Found { Record: MetadataArtifactState state } when state.Length == stamp.Identity.Length
                        => new(true, state.LiveReferences, state.Revision.Value),
                    MetadataReadItem.NotFound => new(true, 0, Guid.NewGuid()),
                    _ => new(false, 0, Guid.Empty)
                };
            });
        var controls = new MetadataFixtureControls();
        var publication = new ArtifactMetadataPublicationAuthority(artifacts.Identity, artifacts.Validator, artifacts.Authority);
        metadata = metadataProvider == "sqlite"
            ? new SqliteMetadataStore(Path.Combine(root, "metadata.db"), publication, TimeProvider.System, controls.ObserveAsync, controls.Diagnose)
            : new MemoryMetadataStore(publication, TimeProvider.System, controls.ObserveAsync, controls.Diagnose);
        var session = new ArtifactMetadataFixtureSession(artifacts, metadata, publication, controls);
        try
        {
            var result = await ((IMetadataSchemaAdministration)metadata).PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default);
            if (result is not MetadataResult<MetadataSchemaAdmission>.Success)
            { throw new InvalidOperationException("Artifact metadata fixture schema admission failed."); }
            return session;
        }
        catch { await session.DisposeAsync(); throw; }
    }

    public Task WhenMetadataIdleAsync() => Metadata switch
    {
        SqliteMetadataStore sqlite => sqlite.WhenIdleAsync(),
        MemoryMetadataStore memory => memory.WhenIdleAsync(),
        _ => throw new InvalidOperationException("Unknown artifact metadata fixture.")
    };

    public Task CloseAdmissionsAndObserveSettlementForQualificationAsync()
    {
        lock (shutdownSync) { return shutdown ??= CloseAndSettleAsync(); }
    }

    private async Task CloseAndSettleAsync()
    {
        var authoritySettlement = Artifacts.Authority.CloseAdmissionsAndObserveSettlementForQualificationAsync();
        var metadataDisposal = Metadata.DisposeAsync().AsTask();
        var metadataSettlement = Metadata switch
        {
            SqliteMetadataStore sqlite => sqlite.ObserveLifetimeSettlementForTest(),
            MemoryMetadataStore memory => memory.ObserveWorkSettlementForTest(),
            _ => throw new InvalidOperationException("Unknown artifact metadata fixture.")
        };
        var artifactDisposal = Artifacts.DisposeAsync().AsTask();
        await Task.WhenAll(authoritySettlement, metadataDisposal, metadataSettlement, artifactDisposal);
    }

    public async ValueTask DisposeAsync()
    {
        await Metadata.DisposeAsync();
        await Artifacts.DisposeAsync();
    }
}
