using System.Globalization;
using System.Text;
using System.Text.Json;
using Hoard.Testing.Conformance.Evidence;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;

namespace Hoard.Conformance.TestLogger;

internal static class RuntimeOriginOutput
{
    private sealed record Pending(int Count, string Digest, List<string> Parts);
    internal readonly record struct ComponentIdentity(string Assembly, Guid Module, string Type);

    internal static (JsonElement[] Origins, bool Unknown, Dictionary<Guid, ComponentIdentity> Instances) Read(
        TestResult result, RuntimeInput input, RuntimeExpectedTest expected, HashSet<Guid> priorSessions,
        IReadOnlyDictionary<Guid, ComponentIdentity> priorInstances)
    {
        var pending = new Dictionary<Guid, Pending>();
        var unknown = false;
        var total = 0;
        RuntimeSafety.Require(result.Messages.Count <= 4096, "OutputLimitExceeded");
        foreach (var message in result.Messages)
        {
            RuntimeSafety.Require(message.Text is { Length: <= 1024 * 1024 }, "OutputLimitExceeded");
            total += Encoding.UTF8.GetByteCount(message.Text);
            RuntimeSafety.Require(total <= 1024 * 1024, "OutputLimitExceeded");
            if (message.Category != TestResultMessage.StandardOutCategory) { unknown = true; continue; }
            foreach (var span in message.Text.AsSpan().EnumerateLines())
            {
                if (span.IsEmpty) { continue; }
                RuntimeSafety.Require(span.Length <= 1024, "OutputLimitExceeded");
                var line = span.ToString();
                if (!line.StartsWith(ConformanceSessionOriginOutput.Prefix + ":", StringComparison.Ordinal))
                { unknown = true; continue; }
                var fields = line.Split(':');
                RuntimeSafety.Require(fields.Length == 6, "ProofMismatch");
                var id = Uuid(fields[1]);
                RuntimeSafety.Require(!priorSessions.Contains(id), "EvidenceIncomplete");
                var index = Number(fields[2]);
                var count = Number(fields[3]);
                RuntimeSafety.Require(count is > 0 and <= 171 && index < count, "OutputLimitExceeded");
                RuntimeSafety.Digest(fields[4]);
                RuntimeSafety.Require(fields[5].Length is > 0 and <= 512
                    && (index == count - 1 || fields[5].Length == 512)
                    && fields[5].All(c => char.IsAsciiLetterOrDigit(c) || c is '+' or '/' or '='), "ProofMismatch");
                if (!pending.TryGetValue(id, out var packet))
                {
                    RuntimeSafety.Require(pending.Count < 128, "OutputLimitExceeded");
                    packet = new(count, fields[4], []);
                    pending.Add(id, packet);
                }
                RuntimeSafety.Require(packet.Count == count && packet.Digest == fields[4], "ProofMismatch");
                RuntimeSafety.Require(index == packet.Parts.Count, "EvidenceIncomplete");
                packet.Parts.Add(fields[5]);
            }
        }
        var origins = new List<JsonElement>();
        var instances = new Dictionary<Guid, ComponentIdentity>();
        foreach (var (id, packet) in pending)
        {
            RuntimeSafety.Require(packet.Parts.Count == packet.Count, "EvidenceIncomplete");
            var encoded = string.Concat(packet.Parts);
            byte[] bytes;
            try { bytes = Convert.FromBase64String(encoded); }
            catch (FormatException) { throw RuntimeSafety.Error("ProofMismatch"); }
            RuntimeSafety.Require(bytes.Length <= 64 * 1024, "OutputLimitExceeded");
            RuntimeSafety.Require(Convert.ToBase64String(bytes) == encoded
                && RuntimeSafety.Hash(bytes) == packet.Digest, "ProofMismatch");
            using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 8 });
            var origin = document.RootElement;
            Keys(origin, "schemaVersion", "runId", "caseId", "sessionId", "parentSessionId",
                "factoryOperation", "descriptorSha256", "runtimeVersion", "processArchitecture", "components");
            RuntimeSafety.Require(origin.GetProperty("schemaVersion").GetInt32() == 1
                && Uuid(origin.GetProperty("runId").GetString()!) == input.RunId
                && Uuid(origin.GetProperty("sessionId").GetString()!) == id
                && origin.GetProperty("caseId").GetString() == expected.CaseId, "ProofMismatch");
            var parentElement = origin.GetProperty("parentSessionId");
            Guid? parent = parentElement.ValueKind == JsonValueKind.Null ? null : Uuid(parentElement.GetString()!);
            RuntimeSafety.Require(parent != id && origin.GetProperty("factoryOperation").GetString()
                == (parent.HasValue ? "reopen" : "create"), "ProofMismatch");
            RuntimeSafety.Digest(origin.GetProperty("descriptorSha256").GetString()!);
            var runtime = origin.GetProperty("runtimeVersion").GetString();
            RuntimeSafety.Require(runtime is { Length: <= 32 } && Version.TryParse(runtime, out var version)
                && version.ToString() == runtime && version.Build >= 0, "ProofMismatch");
            RuntimeSafety.Require(origin.GetProperty("processArchitecture").GetString() is "x64" or "arm64", "ProofMismatch");
            var components = origin.GetProperty("components");
            var roles = components.ValueKind == JsonValueKind.Object
                ? components.EnumerateObject().Select(property => property.Name).ToHashSet(StringComparer.Ordinal) : [];
            string[] metadata = ["factory", "session", "store", "schema", "authority", "faults"];
            string[] artifacts = ["factory", "session", "store", "validator", "maintenance", "lifetime", "authority", "faults"];
            RuntimeSafety.Require(roles.SetEquals(metadata) || roles.SetEquals(artifacts), "ProofMismatch");
            Keys(components, roles.ToArray());
            foreach (var role in components.EnumerateObject())
            {
                var component = role.Value;
                Keys(component, "instanceId", "assemblySha256", "moduleVersionId", "typeSha256");
                var instance = Uuid(component.GetProperty("instanceId").GetString()!);
                var assembly = component.GetProperty("assemblySha256").GetString()!;
                var module = Uuid(component.GetProperty("moduleVersionId").GetString()!);
                var type = component.GetProperty("typeSha256").GetString()!;
                RuntimeSafety.Digest(assembly);
                RuntimeSafety.Digest(type);
                RuntimeSafety.Require(input.Assemblies.Any(file => file.Sha256 == assembly), "ProofMismatch");
                var identity = new ComponentIdentity(assembly, module, type);
                RuntimeSafety.Require(!instances.TryGetValue(instance, out var prior) || prior == identity, "ProofMismatch");
                RuntimeSafety.Require(!priorInstances.TryGetValue(instance, out var previous) || previous == identity, "ProofMismatch");
                instances[instance] = identity;
            }
            origins.Add(origin.Clone());
        }
        return (origins.ToArray(), unknown, instances);
    }

    private static void Keys(JsonElement value, params string[] expected)
    {
        RuntimeSafety.Require(value.ValueKind == JsonValueKind.Object, "ProofMismatch");
        var names = value.EnumerateObject().Select(property => property.Name).ToArray();
        RuntimeSafety.Require(names.Length == expected.Length
            && names.ToHashSet(StringComparer.Ordinal).SetEquals(expected), "ProofMismatch");
    }

    private static Guid Uuid(string value)
    {
        RuntimeSafety.Require(Guid.TryParseExact(value, "D", out var id) && id != Guid.Empty
            && id.ToString("D") == value, "ProofMismatch");
        return id;
    }

    private static int Number(string value)
    {
        RuntimeSafety.Require(int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var number)
            && number >= 0 && number.ToString(CultureInfo.InvariantCulture) == value, "ProofMismatch");
        return number;
    }
}
