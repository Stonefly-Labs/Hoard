using System.Collections.Immutable;
using System.Runtime.InteropServices;
using System.Text.Json;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceOriginalObservationOutput
{
    public const string Prefix = "hoard-original-v1";
    public const string ContextVariable = "HOARD_ORIGINAL_CONTEXT";

    public static void WriteIfRequested(ITestOutputHelper output, string testIdentity, string? bindingId,
        string kind, params (string Role, object Component)[] components)
    {
        var encoded = Environment.GetEnvironmentVariable(ContextVariable);
        if (encoded is null) { return; }
        try
        {
            if (encoded.Length is 0 or > 128 * 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
            var bytes = Convert.FromBase64String(encoded);
            if (bytes.Length > 64 * 1024 || Convert.ToBase64String(bytes) != encoded)
            { throw new InvalidOperationException("ProofMismatch"); }
            using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 4 });
            var root = document.RootElement;
            var keys = root.EnumerateObject().Select(property => property.Name).ToArray();
            if (keys.Length != 3 || !keys.ToHashSet(StringComparer.Ordinal)
                    .SetEquals(["schemaVersion", "runId", "cases"])
                || root.GetProperty("schemaVersion").GetInt32() != 1)
            { throw new InvalidOperationException("ProofMismatch"); }
            var runText = root.GetProperty("runId").GetString();
            if (!Guid.TryParseExact(runText, "D", out var runId) || runId == Guid.Empty || runId.ToString("D") != runText)
            { throw new InvalidOperationException("ProofMismatch"); }
            var cases = root.GetProperty("cases").EnumerateObject().ToArray();
            if (cases.Length is 0 or > 10000
                || cases.Select(property => property.Name).Distinct(StringComparer.Ordinal).Count() != cases.Length)
            { throw new InvalidOperationException("ProofMismatch"); }
            var matches = cases.Where(property => property.Name == testIdentity).ToArray();
            if (matches.Length != 1) { throw new InvalidOperationException("WitnessMissing"); }
            var context = matches[0].Value;
            var fields = context.EnumerateObject().Select(property => property.Name).ToArray();
            if (fields.Length != 2 || !fields.ToHashSet(StringComparer.Ordinal).SetEquals(["bindingId", "caseId"]))
            { throw new InvalidOperationException("ProofMismatch"); }
            var selected = context.GetProperty("bindingId").GetString()!;
            if (bindingId is not null && bindingId != selected) { throw new InvalidOperationException("ProofMismatch"); }
            Write(output, ConformanceOriginalObservation.Capture(
                runId, context.GetProperty("caseId").GetString()!, testIdentity, selected, kind, components));
        }
        catch (Exception error) when (error is FormatException or JsonException or KeyNotFoundException)
        { throw new InvalidOperationException("ProofMismatch"); }
    }

    public static ImmutableArray<string> Render(ConformanceOriginalObservation observation)
    {
        ArgumentNullException.ThrowIfNull(observation);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            runId = observation.RunId,
            caseId = observation.CaseId,
            testIdentity = observation.TestIdentity,
            bindingId = observation.BindingId,
            observationId = observation.ObservationId,
            parentObservationId = observation.ParentObservationId,
            kind = observation.Kind,
            operation = observation.Operation,
            runtimeVersion = Environment.Version.ToString(),
            processArchitecture = RuntimeInformation.ProcessArchitecture.ToString().ToLowerInvariant(),
            components = observation.Components.ToDictionary(pair => pair.Key, pair => new
            {
                instanceId = pair.Value.InstanceId,
                assemblySha256 = pair.Value.Assembly.AssemblySha256,
                moduleVersionId = pair.Value.Assembly.ModuleVersionId,
                typeSha256 = pair.Value.Assembly.TypeSha256
            }, StringComparer.Ordinal)
        });
        return ConformanceEvidencePacket.Render(Prefix, observation.ObservationId, bytes);
    }

    public static void Write(ITestOutputHelper output, ConformanceOriginalObservation observation)
    {
        ArgumentNullException.ThrowIfNull(output);
        foreach (var packet in Render(observation)) { output.WriteLine(packet); }
    }
}
