using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Fixtures.Conformance.Bindings.Mutations;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Fixtures.Conformance.Consumer;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Conformance.Tests;

public sealed class CategoryMutationTests
{
    [Theory]
    [InlineData("memory")]
    [InlineData("sqlite")]
    public Task Stale_metadata_replay_is_rejected(string provider) => MetadataReplayAsync(provider, false);

    [Theory]
    [InlineData("memory")]
    [InlineData("sqlite")]
    public Task Corrected_metadata_replay_passes(string provider) => MetadataReplayAsync(provider, true);

    private static async Task MetadataReplayAsync(string provider, bool corrected)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var context = Context(clock, resources);
        IMetadataConformanceBinding binding = provider switch
        {
            "memory" => new MemoryBinding(Package("HOARD_METADATA_MEMORY_PACKAGE_SHA256")),
            "sqlite" => new SqliteBinding(Package("HOARD_METADATA_SQLITE_PACKAGE_SHA256")),
            _ => throw new ArgumentException("BindingInvalid")
        };
        await using var session = await binding.CreateSessionAsync(context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var store = new StaleOperationStore(session.Store, !corrected);
        try { await MetadataTimeAssertions.TicketExpiryAndRollbackAsync(store, clock, default); }
        finally { Assert.Equal(corrected ? 0 : 1, store.Replays); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public Task Premature_artifact_publication_is_rejected(string provider) => ArtifactVisibilityAsync(provider, false);

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public Task Corrected_artifact_staging_passes(string provider) => ArtifactVisibilityAsync(provider, true);

    private static async Task ArtifactVisibilityAsync(string provider, bool corrected)
    {
        await using var resources = new LocalArtifactSessionTests.RecordingDirectories();
        var options = new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid())));
        IArtifactConformanceBinding binding = provider switch
        {
            "local" => new LocalBinding(Package("HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256"), options: options),
            "object" => new ObjectSemanticsBinding(Package("HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256"), options: options),
            _ => throw new ArgumentException("BindingInvalid")
        };
        await using var session = await binding.CreateSessionAsync(Context(TimeProvider.System, resources), default);
        await using var store = new PrematurePublicationStore(session.Store, !corrected);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = await session.Faults.ObserveBoundaryAsync(ArtifactObservationPoint.StagePrefix,
            () => { entered.TrySetResult(); return new(release.Task); }, default);
        try
        {
            await ArtifactPublicationAssertions.PrivateStagingAsync(store,
                token => entered.Task.WaitAsync(TimeSpan.FromSeconds(5), token),
                () => release.TrySetResult(), default);
        }
        finally
        {
            release.TrySetResult();
            Assert.Equal(corrected ? 0 : 1, store.Publications);
        }
    }

    private static ConformanceRunContext Context(TimeProvider clock, IConformanceResourceAllocator resources) =>
        new(Guid.ParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID")
            ?? throw new InvalidOperationException("PrerequisiteMissing"), "D"),
            "category-mutation", clock, resources, new ConformanceEvidenceBuffer());

    private static string Package(string variable) => Environment.GetEnvironmentVariable(variable)
        ?? throw new InvalidOperationException("PrerequisiteMissing");
}
