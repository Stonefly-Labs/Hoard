#if HOARD_ARTIFACT_CONTRIBUTOR
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Sdk;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class ArtifactContributorProcess
{
    private sealed class InputException(ConformanceDiagnosticCode code) : Exception
    {
        internal ConformanceDiagnosticCode Code { get; } = code;
    }

    private sealed record Request(string Action, string Boundary, Guid RunId, string CaseId,
        string ResourceId, int Descriptor, string RepositoryRoot, string StatePath,
        string OriginPath, string ReadbackPath, Guid? SourceSessionId, string? StateSha256);

    private static async Task<int> Main(string[] args)
    {
        try
        {
            Check(OperatingSystem.IsLinux(), ConformanceDiagnosticCode.PrerequisiteMissing);
            Check(args.Length == 4 && args[0] is "artifact-crash" or "artifact-transfer",
                ConformanceDiagnosticCode.EvidenceSchemaInvalid);
            var requestHash = ConformanceBindingDeclaration.Hash(args[3]);
            using var files = new ConformanceControlFiles(args[1]);
            var bytes = files.Read(args[2], 16384);
            Check(Hash(bytes) == requestHash, ConformanceDiagnosticCode.InputChanged);
            using var cancellation = new CancellationTokenSource(TimeSpan.FromMinutes(args[0] == "artifact-transfer" ? 40 : 5));
            try
            {
                if (args[0] == "artifact-transfer")
                {
                    await ArtifactContributorTransfer.ExecuteAsync(files, args[1], bytes, cancellation.Token);
                }
                else
                {
                    var request = Parse(bytes);
                    Check(ContributorBindingFactory.ExpectedDurability == ArtifactDurability.LocalProcessCrash,
                        ConformanceDiagnosticCode.UnsupportedProfile);
                    await ExecuteAsync(files, args[1], request, requestHash, cancellation.Token);
                }
            }
            finally
            {
                Check(Hash(files.Read(args[2], 16384)) == requestHash, ConformanceDiagnosticCode.InputChanged);
            }
            return 0;
        }
        catch (Exception error)
        {
            var code = error switch
            {
                InputException input => input.Code,
                XunitException => ConformanceDiagnosticCode.AssertionFailed,
                OperationCanceledException => ConformanceDiagnosticCode.DeadlineExceeded,
                PlatformNotSupportedException => ConformanceDiagnosticCode.PrerequisiteMissing,
                JsonException or FormatException or ArgumentException => ConformanceDiagnosticCode.EvidenceSchemaInvalid,
                _ => ConformanceDiagnosticCode.UnknownDiagnostic
            };
            await ConformanceDiagnostic.WriteAsync(Console.OpenStandardOutput(), code, 0, default);
            return 2;
        }
    }

    private static async Task ExecuteAsync(ConformanceControlFiles files, string root, Request request,
        string requestHash, CancellationToken cancellationToken)
    {
        var resource = new ConformanceOwnedDirectory(request.ResourceId,
            Path.Combine(root, "stores", request.ResourceId));
        var recovery = request.Action == "recover";
        using var allocator = ConformanceResourceAllocator.OpenControllerLease(
            resource, request.Descriptor, request.RepositoryRoot, recovery);
        var context = new ConformanceRunContext(request.RunId, request.CaseId, TimeProvider.System,
            allocator, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        if (!recovery)
        {
            await using var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, cancellationToken);
            ContributorArtifactSessionTests.AssertProfile(session);
            await ArtifactCrashAssertions.CrashAsync(session.Store, session.Maintenance, session.Identity,
                request.Boundary, request.RunId, async state =>
                {
                    ContributorArtifactSessionTests.AssertProfile(session);
                    var sourceStateBytes = JsonSerializer.SerializeToUtf8Bytes(state);
                    var origin = session.CaptureOrigin();
                    var originBytes = ConformanceSessionOriginOutput.Serialize(origin);
                    files.Write(request.StatePath, sourceStateBytes, 16384);
                    files.Write(request.OriginPath, originBytes, 65536);
                    files.Write(request.ReadbackPath, JsonSerializer.SerializeToUtf8Bytes(new
                    {
                        schemaVersion = 1,
                        qualification = false,
                        kind = "artifact-crash-source",
                        runId = request.RunId,
                        caseId = request.CaseId,
                        boundary = request.Boundary,
                        sessionId = origin.SessionId,
                        stateSha256 = Hash(sourceStateBytes),
                        originSha256 = Hash(originBytes)
                    }), 16384);
                    await EmitAsync("barrier", BoundaryValue(request.Boundary));
                    await Task.Delay(TimeSpan.FromMinutes(4), cancellationToken);
                    throw new InputException(ConformanceDiagnosticCode.DeadlineExceeded);
                }, (point, callback) => session.Faults.ObserveBoundaryAsync(point switch
                {
                    ArtifactCrashPoint.StagePrefix => ArtifactObservationPoint.StagePrefix,
                    ArtifactCrashPoint.StageVerified => ArtifactObservationPoint.StageVerified,
                    ArtifactCrashPoint.PublicationSelected => ArtifactObservationPoint.PublicationSelected,
                    ArtifactCrashPoint.DeleteRemoved => ArtifactObservationPoint.DeleteRemoved,
                    ArtifactCrashPoint.DeleteReclaimed => ArtifactObservationPoint.DeleteReclaimed,
                    _ => throw new InputException(ConformanceDiagnosticCode.BindingInvalid)
                }, callback, cancellationToken), cancellationToken);
            throw new InputException(ConformanceDiagnosticCode.WitnessMissing);
        }

        Check(binding is IArtifactRecoveryConformanceBinding, ConformanceDiagnosticCode.BindingInvalid);
        var stateBytes = files.Read(request.StatePath, 16384);
        Check(Hash(stateBytes) == request.StateSha256, ConformanceDiagnosticCode.InputChanged);
        var recovered = JsonSerializer.Deserialize<ArtifactCrashState>(stateBytes,
            new JsonSerializerOptions { MaxDepth = 32 })
            ?? throw new InputException(ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        Check(recovered.Run == request.RunId && recovered.Barrier == request.Boundary,
            ConformanceDiagnosticCode.ProofMismatch);
        await using (var session = await ConformanceObservedArtifactRecoverySession.OpenAsync(
            (IArtifactRecoveryConformanceBinding)binding, context, recovered.Store,
            request.SourceSessionId!.Value, requestHash, cancellationToken))
        {
            ContributorArtifactSessionTests.AssertProfile(session);
            var result = await ArtifactCrashAssertions.RecoverAsync(
                session.Store, session.Maintenance, recovered, request.Boundary, request.RunId, cancellationToken);
            ContributorArtifactSessionTests.AssertProfile(session);
            files.Write(request.OriginPath, ConformanceSessionOriginOutput.Serialize(session.CaptureOrigin()), 65536);
            Check(Enum.IsDefined(result.Outcome.Outcome) && result.Outcome.ReceiptId != Guid.Empty,
                ConformanceDiagnosticCode.ProofMismatch);
            files.Write(request.ReadbackPath, JsonSerializer.SerializeToUtf8Bytes(new
            {
                schemaVersion = 1,
                qualification = false,
                runId = request.RunId,
                caseId = request.CaseId,
                boundary = request.Boundary,
                ownerFenced = result.OwnerFenced,
                reconstructed = result.Reconstructed,
                reclamation = result.Reclamation,
                contentSha256 = result.ContentSha256,
                contentLength = result.ContentLength,
                controlSha256 = result.ControlSha256,
                controlLength = result.ControlLength,
                outcome = result.Outcome.Outcome.ToString(),
                receiptId = result.Outcome.ReceiptId
            }), 16384);
        }
        Check(Hash(files.Read(request.StatePath, 16384)) == request.StateSha256, ConformanceDiagnosticCode.InputChanged);
        await EmitAsync("test", 1);
    }

    private static Request Parse(byte[] bytes)
    {
        using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 8 });
        var value = document.RootElement;
        Check(value.ValueKind == JsonValueKind.Object, ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        var keys = value.EnumerateObject().Select(property => property.Name).ToArray();
        string[] expected = ["schemaVersion", "qualification", "action", "boundary", "runId", "caseId",
            "resourceId", "descriptor", "repositoryRoot", "statePath", "originPath", "readbackPath",
            "sourceSessionId", "stateSha256"];
        Check(keys.Length == expected.Length && keys.ToHashSet(StringComparer.Ordinal).SetEquals(expected)
            && value.GetProperty("schemaVersion").GetInt32() == 1
            && value.GetProperty("qualification").ValueKind == JsonValueKind.False,
            ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        string Text(string name) => value.GetProperty(name).GetString()
            ?? throw new InputException(ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        var action = Text("action");
        var boundary = Text("boundary");
        _ = BoundaryValue(boundary);
        Check(action is "source" or "recover", ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        var run = Guid.Parse(Text("runId"));
        Check(run != Guid.Empty, ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        var resource = ConformanceBindingDeclaration.Id(Text("resourceId"));
        var state = Text("statePath");
        var origin = Text("originPath");
        var readback = Text("readbackPath");
        Check(state.StartsWith("stores/", StringComparison.Ordinal)
            && !state.StartsWith("stores/" + resource + "/", StringComparison.Ordinal)
            && origin.StartsWith("proofs/", StringComparison.Ordinal)
            && readback.StartsWith("proofs/", StringComparison.Ordinal) && origin != readback,
            ConformanceDiagnosticCode.OwnershipInvalid);
        Guid? source = null;
        string? stateHash = null;
        if (action == "recover")
        {
            source = Guid.Parse(Text("sourceSessionId"));
            Check(source != Guid.Empty, ConformanceDiagnosticCode.EvidenceSchemaInvalid);
            stateHash = ConformanceBindingDeclaration.Hash(Text("stateSha256"));
        }
        else
        {
            Check(value.GetProperty("sourceSessionId").ValueKind == JsonValueKind.Null
                && value.GetProperty("stateSha256").ValueKind == JsonValueKind.Null,
                ConformanceDiagnosticCode.EvidenceSchemaInvalid);
        }
        return new(action, boundary, run, ConformanceBindingDeclaration.Id(Text("caseId")),
            resource, value.GetProperty("descriptor").GetInt32(), Text("repositoryRoot"),
            state, origin, readback, source, stateHash);
    }

    private static int BoundaryValue(string boundary) => boundary switch
    {
        "B0" => 40, "B1" => 41, "B2" => 42, "B3" => 43, "D0" => 44, "D1" => 45,
        _ => throw new InputException(ConformanceDiagnosticCode.EvidenceSchemaInvalid)
    };

    private static async Task EmitAsync(string kind, int value)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { @event = kind, code = "None", value }));
        await Console.Out.FlushAsync();
    }

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
    private static void Check(bool condition, ConformanceDiagnosticCode code)
    {
        if (!condition) { throw new InputException(code); }
    }
}
#endif
