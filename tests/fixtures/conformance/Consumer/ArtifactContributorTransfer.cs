#if HOARD_ARTIFACT_CONTRIBUTOR
using System.Runtime.InteropServices;
using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class ArtifactContributorTransfer
{
    internal static async Task ExecuteAsync(
        ConformanceControlFiles files, string root, byte[] requestBytes, CancellationToken cancellationToken)
    {
        using var document = JsonDocument.Parse(requestBytes, new JsonDocumentOptions { MaxDepth = 8 });
        var request = document.RootElement;
        Check(request.ValueKind == JsonValueKind.Object);
        var keys = request.EnumerateObject().Select(property => property.Name).ToArray();
        string[] fields = ["schemaVersion", "qualification", "resourceId", "runId", "caseId",
            "repositoryRoot", "originPath", "readbackPath", "size", "expectedSha256"];
        Check(keys.Length == fields.Length && keys.ToHashSet(StringComparer.Ordinal).SetEquals(fields)
            && request.GetProperty("schemaVersion").GetInt32() == 1
            && request.GetProperty("qualification").ValueKind == JsonValueKind.False);
        string Text(string name) => request.GetProperty(name).GetString() ?? throw new ArgumentException("EvidenceSchemaInvalid");
        var runId = Guid.Parse(Text("runId"));
        Check(runId != Guid.Empty);
        var resource = ConformanceBindingDeclaration.Id(Text("resourceId"));
        var caseId = ConformanceBindingDeclaration.Id(Text("caseId"));
        var prefix = "proofs/contributor-transfer-" + resource;
        var originPath = Text("originPath");
        var readbackPath = Text("readbackPath");
        Check(originPath == prefix + "-origin.json" && readbackPath == prefix + "-readback.json");
        var size = request.GetProperty("size").GetInt64();
        Check(size is 268435456L or 4294967296L);
        var expected = ConformanceBindingDeclaration.Hash(Text("expectedSha256"));
        using var allocator = ConformanceResourceAllocator.Open(
            Path.Combine(root, "stores", resource), Text("repositoryRoot"));
        var context = new ConformanceRunContext(runId, caseId, TimeProvider.System, allocator, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(
            limits: new ArtifactLimits(transferSlots: 1), references: (_, _) =>
                ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await using (var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, cancellationToken))
        {
            ContributorArtifactSessionTests.AssertProfile(session);
            await ArtifactTransferAssertions.WarmAsync(session.Store, cancellationToken);
            GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
            await EmitAsync("control", 0);
            Check(await Console.In.ReadLineAsync(cancellationToken) == "transfer");
            var transferred = await ArtifactTransferAssertions.TransferAsync(session.Store, size, expected, cancellationToken);
            ContributorArtifactSessionTests.AssertProfile(session);
            files.Write(originPath, ConformanceSessionOriginOutput.Serialize(session.CaptureOrigin()), 65536);
            files.Write(readbackPath, JsonSerializer.SerializeToUtf8Bytes(new
            {
                eventName = "complete",
                provider = ContributorBindingFactory.BindingId,
                runId,
                pid = Environment.ProcessId,
                size,
                written = transferred.Written,
                read = transferred.Read,
                expectedSha256 = expected,
                sourceSha256 = transferred.SourceSha256,
                sinkSha256 = transferred.SinkSha256,
                runtime = RuntimeInformation.FrameworkDescription,
                sourcePaced = transferred.SourcePaced,
                sinkPaced = transferred.SinkPaced,
                nonSeekable = true,
                generated = true,
                independentExpectedHash = true,
                warmupComplete = true,
                bufferBytes = session.Store.Capabilities.Limits.CopyBufferBytes,
                providerBufferLimit = session.Store.Capabilities.Limits.TransferBufferBytes,
                slots = session.Store.Capabilities.Limits.TransferSlots
            }), 8192);
            await EmitAsync("test", size);
            Check(await Console.In.ReadLineAsync(cancellationToken) == "settle");
        }
        await EmitAsync("control", 1);
    }

    private static void Check(bool condition)
    {
        if (!condition) { throw new ArgumentException("EvidenceSchemaInvalid"); }
    }

    private static async Task EmitAsync(string kind, long value)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { @event = kind, code = "None", value }));
        await Console.Out.FlushAsync(cancellationToken: default);
    }
}
#endif
