#if HOARD_ARTIFACT_CONTRIBUTOR
using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class ArtifactContributorNonCooperation
{
    internal static async Task ExecuteAsync(
        ConformanceControlFiles files, string root, byte[] requestBytes, CancellationToken cancellationToken)
    {
        using var document = JsonDocument.Parse(requestBytes, new JsonDocumentOptions { MaxDepth = 8 });
        var request = document.RootElement;
        Check(request.ValueKind == JsonValueKind.Object);
        var keys = request.EnumerateObject().Select(property => property.Name).ToArray();
        string[] fields = ["schemaVersion", "qualification", "resourceId", "runId", "caseId",
            "repositoryRoot", "originPath", "readbackPrefix", "scenario"];
        Check(keys.Length == fields.Length && keys.ToHashSet(StringComparer.Ordinal).SetEquals(fields)
            && request.GetProperty("schemaVersion").GetInt32() == 1
            && request.GetProperty("qualification").ValueKind == JsonValueKind.False);
        string Text(string name) => request.GetProperty(name).GetString() ?? throw new ArgumentException("EvidenceSchemaInvalid");
        var runId = Guid.Parse(Text("runId"));
        Check(runId != Guid.Empty);
        var resource = ConformanceBindingDeclaration.Id(Text("resourceId"));
        var caseId = ConformanceBindingDeclaration.Id(Text("caseId"));
        var prefix = "proofs/contributor-noncooperation-" + resource;
        var originPath = Text("originPath");
        Check(originPath == prefix + "-origin.json" && Text("readbackPrefix") == prefix);
        var scenario = Text("scenario");
        Check(scenario is "source" or "destination" or "native");
        using var allocator = ConformanceResourceAllocator.Open(
            Path.Combine(root, "stores", resource), Text("repositoryRoot"));
        var context = new ConformanceRunContext(runId, caseId, TimeProvider.System, allocator, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(
            limits: new ArtifactLimits(transferSlots: 1, waitingCalls: 0), references: (_, _) =>
                ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, cancellationToken);
        ContributorArtifactSessionTests.AssertProfile(session);
        await ArtifactNonCooperationAssertions.ExecuteAsync(
            session.Store, session.Lifetime, session.Authority, session.Identity, scenario,
            session.Faults.HoldSynchronousStorageAsync, session.Faults.ObserveWorkerSettlement,
            session.Faults.ObserveInitialization, session.Faults.ProbeCompetingInitializationAsync,
            async (phase, readback) =>
            {
                ContributorArtifactSessionTests.AssertProfile(session);
                if (phase == "contained")
                { files.Write(originPath, ConformanceSessionOriginOutput.Serialize(session.CaptureOrigin()), 65536); }
                files.Write(prefix + "-" + phase + ".json", JsonSerializer.SerializeToUtf8Bytes(new
                {
                    eventName = "noncooperative",
                    phase,
                    pid = Environment.ProcessId,
                    runId,
                    provider = ContributorBindingFactory.BindingId,
                    scenario,
                    durableCrashProof = false,
                    cleanup = readback.Cleanup.ToString(),
                    callerCode = readback.CallerCode.ToString(),
                    admissionCode = readback.AdmissionCode.ToString(),
                    shutdownCode = readback.ShutdownCode.ToString(),
                    enteredWorkers = readback.EnteredWorkers,
                    workerPending = readback.WorkerPending,
                    borrowedStreamsIntact = readback.BorrowedStreamsIntact,
                    rootStillOwned = readback.RootStillOwned,
                    readinessBlocked = readback.ReadinessBlocked,
                    protectionRetained = readback.ProtectionRetained
                }), 8192);
                var offset = scenario switch { "source" => 0, "destination" => 1, "native" => 2, _ => throw new ArgumentException() };
                Console.WriteLine(JsonSerializer.Serialize(new
                { @event = "barrier", code = "None", value = (phase == "contained" ? 60 : 70) + offset }));
                await Console.Out.FlushAsync(cancellationToken);
                if (phase == "contained")
                { Check(await Console.In.ReadLineAsync(cancellationToken) == "inspect"); }
            }, cancellationToken);
    }

    private static void Check(bool condition)
    {
        if (!condition) { throw new ArgumentException("EvidenceSchemaInvalid"); }
    }
}
#endif
