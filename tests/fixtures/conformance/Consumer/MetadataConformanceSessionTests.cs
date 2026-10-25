using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class MetadataConformanceSessionTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("memory", "capacity")]
    [InlineData("memory", "writer")]
    [InlineData("memory", "publication")]
    [InlineData("sqlite", "capacity")]
    [InlineData("sqlite", "writer")]
    [InlineData("sqlite", "publication")]
    public async Task Observed_factories_execute_unchanged_common_consumers_with_actual_origins(
        string provider, string consumer)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await (consumer switch
        {
            "capacity" => MetadataFailureAssertions.StorageCapacityAsync(session.Store,
                token => session.Faults.ArmAsync(ConformanceFault.Capacity, token), default),
            "writer" => MetadataDeadlineAssertions.WriterBudgetAsync(
                session.Store, session.Faults.HoldWriterAsync, session.Faults.AwaitSettlementAsync, default),
            "publication" => MetadataPublicationAssertions.ProtectionThroughSettlementAsync(
                session.Store, session.Authority, session.Faults.ObserveBoundaryAsync, session.Faults.AwaitSettlementAsync, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
        ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
    }

    private static Guid RunId()
    {
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        return runId;
    }

    private static IMetadataConformanceBinding Binding(string provider)
    {
        var variable = provider switch
        {
            "memory" => "HOARD_METADATA_MEMORY_PACKAGE_SHA256",
            "sqlite" => "HOARD_METADATA_SQLITE_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        return provider == "memory" ? new MemoryBinding(sha256) : new SqliteBinding(sha256);
    }
}
