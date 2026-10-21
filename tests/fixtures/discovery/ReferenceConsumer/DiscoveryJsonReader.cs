using System.Collections.Immutable;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Hoard.Discovery.ReferenceConsumer;

public sealed record ConsumerReason(string Code, string CorrectiveAction);
public sealed record ConsumerCapability(string Id, string Version, string OperationId, ImmutableArray<string> Owners,
    ImmutableArray<string> Dependencies, string Support, string EvidenceScope, ImmutableArray<string> EvidenceIds,
    string Availability, ImmutableArray<ConsumerReason> Reasons, bool Understood);
public sealed record ConsumerModule(string Id, string Category, string Inclusion, bool Registered, bool Enabled,
    string Phase, string Readiness, ImmutableArray<ConsumerCapability> Capabilities, ImmutableArray<ConsumerReason> Reasons, bool Understood);
public sealed record ConsumerObservation(string DistributionId, string Completeness, Guid LifecycleId, string Revision,
    DateTimeOffset CapturedAt, DateTimeOffset PublishedAt, DateTimeOffset? AssessedAt,
    string HostPhase, bool StartupAdmission, ImmutableArray<ConsumerModule> Modules);
public sealed record ConsumerReadResult(bool Compatible, string Code, ConsumerObservation? Observation);

public static class DiscoveryJsonReader
{
    private sealed class IncompatibleException : Exception;
    private static readonly HashSet<string> Phases = ["registered", "validating", "constructing", "composing-services",
        "building-host", "composing-routes", "initializing", "assessing-readiness", "running", "stopping", "draining", "cleaning-up", "stopped", "unknown"];
    private static readonly HashSet<string> Readiness = ["disabled", "enabled", "initializing", "ready", "not-ready", "failed", "stopping", "stopped", "unknown"];
    private static readonly HashSet<string> Reasons = ["missing-inclusion", "missing-registration", "disabled", "unsupported",
        "unverified", "dependency-unavailable", "binding-unavailable", "initializing", "not-ready", "stopping", "stopped",
        "observation-unknown", "metadata-suppressed", "observation-unavailable", "deadline", "response-limit",
        "invalid-protection", "invalid-request", "unauthenticated", "forbidden", "cancelled"];

    public static ConsumerReadResult Read(ReadOnlyMemory<byte> input)
    {
        try
        {
            if (input.Length is 0 or > 4 * 1024 * 1024) { throw new IncompatibleException(); }
            using var document = JsonDocument.Parse(input, new() { MaxDepth = 32 });
            var root = document.RootElement;
            Object(root, "schemaVersion", "distribution", "observation", "host", "modules", "reasons", "omittedReasonCount");
            if (root.GetProperty("schemaVersion").ValueKind != JsonValueKind.Number
                || !root.GetProperty("schemaVersion").TryGetInt32(out var version) || version != 1)
            { throw new IncompatibleException(); }
            var distribution = root.GetProperty("distribution");
            Object(distribution, "id", "version", "inventoryCompleteness");
            var distributionId = Id(distribution, "id");
            Version(distribution, "version");
            var completeness = Text(distribution, "inventoryCompleteness", 16);
            if (completeness is not ("complete" or "partial")) { throw new IncompatibleException(); }
            var observation = root.GetProperty("observation");
            Object(observation, "lifecycleId", "revision", "capturedAt", "publishedAt", "readinessAssessedAt");
            if (!Guid.TryParseExact(Text(observation, "lifecycleId", 36), "D", out var lifecycle) || lifecycle == Guid.Empty)
            { throw new IncompatibleException(); }
            var revision = Text(observation, "revision", 20);
            if (revision.Length == 0 || revision[0] is < '1' or > '9' || revision.Any(character => !char.IsAsciiDigit(character)))
            { throw new IncompatibleException(); }
            var captured = Date(observation, "capturedAt");
            var published = Date(observation, "publishedAt");
            var assessed = observation.GetProperty("readinessAssessedAt").ValueKind == JsonValueKind.Null
                ? (DateTimeOffset?)null : Date(observation, "readinessAssessedAt");
            var host = root.GetProperty("host");
            Object(host, "phase", "ready", "startupAdmission");
            var phase = Text(host, "phase", 128);
            Bool(host, "ready");
            var admission = Bool(host, "startupAdmission");
            var modules = Array(root, "modules", 256).Select(Module).ToImmutableArray();
            if (Array(root, "modules", 256).Sum(module => Array(module, "options", 256).Count()) > 4096)
            { throw new IncompatibleException(); }
            if (modules.Select(module => module.Id).Distinct().Count() != modules.Length) { throw new IncompatibleException(); }
            var identities = modules.SelectMany(module => module.Capabilities).Select(capability =>
                $"{capability.Id}/{capability.Version}/{capability.OperationId}/{string.Join(",", capability.Owners.Order(StringComparer.Ordinal))}").ToArray();
            if (identities.Distinct().Count() != identities.Length || modules.Sum(module => module.Capabilities.Length) > 4096)
            { throw new IncompatibleException(); }
            var reasons = ReadReasons(root);
            var understood = Nonnegative(root, "omittedReasonCount") == 0
                && reasons.All(reason => reason.Code != "observation-unknown");
            return new(true, "compatible", new(distributionId, completeness, lifecycle, revision, captured, published,
                assessed, understood && Phases.Contains(phase) ? phase : "unknown", admission, modules));
        }
        catch (Exception error) when (error is JsonException or IncompatibleException)
        { return new(false, "incompatible-discovery-response", null); }
    }

    public static int CompareRevision(string left, string right) =>
        left.Length == right.Length ? string.CompareOrdinal(left, right) : left.Length.CompareTo(right.Length);

    private static ConsumerModule Module(JsonElement module)
    {
        Object(module, "id", "category", "version", "inclusion", "registered", "enabled", "compatibility", "provenance",
            "lifecyclePhase", "readiness", "selectedRoles", "options", "capabilities", "reasons", "omittedReasonCount");
        var id = Id(module, "id");
        Version(module, "version");
        var category = Text(module, "category", 128);
        var inclusion = Text(module, "inclusion", 128);
        var phase = Text(module, "lifecyclePhase", 128);
        var readiness = Text(module, "readiness", 128);
        var compatibility = module.GetProperty("compatibility");
        Object(compatibility, "hostRange", "abstractionsRange", "allowHostPrerelease", "allowAbstractionsPrerelease");
        Text(compatibility, "hostRange", 128);
        Text(compatibility, "abstractionsRange", 128);
        Bool(compatibility, "allowHostPrerelease");
        Bool(compatibility, "allowAbstractionsPrerelease");
        var provenance = module.GetProperty("provenance");
        Object(provenance, "classification");
        var classification = Text(provenance, "classification", 128);
        OptionalText(provenance, "publisher", 160);
        var roles = Strings(module, "selectedRoles", 3, 32);
        var options = Array(module, "options", 256).ToArray();
        var optionIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var option in options)
        {
            Object(option, "id", "type", "required", "secret");
            if (!optionIds.Add(Id(option, "id"))) { throw new IncompatibleException(); }
            var type = Text(option, "type", 128);
            Bool(option, "required");
            var secret = Bool(option, "secret");
            if (secret != (type == "secret") || secret && (option.TryGetProperty("publicDefault", out _)
                || option.TryGetProperty("allowedValues", out _)))
            { throw new IncompatibleException(); }
            OptionalText(option, "description", 512);
            OptionalText(option, "publicDefault", 512);
            if (option.TryGetProperty("allowedValues", out _)) { Strings(option, "allowedValues", 64, 160); }
            if (option.TryGetProperty("constraints", out var constraints))
            {
                Object(constraints);
                foreach (var property in constraints.EnumerateObject())
                {
                    if (property.Name is "minimumLength" or "maximumLength")
                    {
                        if (property.Value.ValueKind != JsonValueKind.Number || !property.Value.TryGetInt32(out var limit)
                            || limit is < 0 or > 16384) { throw new IncompatibleException(); }
                    }
                    else if (property.Name is "minimum" or "maximum")
                    {
                        if (!long.TryParse(Text(constraints, property.Name, 20), NumberStyles.AllowLeadingSign,
                            CultureInfo.InvariantCulture, out _)) { throw new IncompatibleException(); }
                    }
                }
            }
        }
        var capabilities = Array(module, "capabilities", 64).Select(Capability).ToImmutableArray();
        var reasons = ReadReasons(module);
        return new(id, category, inclusion, Bool(module, "registered"), Bool(module, "enabled"), phase, readiness,
            capabilities, reasons, Nonnegative(module, "omittedReasonCount") == 0
                && reasons.All(reason => reason.Code != "observation-unknown")
                && category is "protocol" or "metadata" or "artifact" or "identity"
                && inclusion is "included" or "unknown" && Phases.Contains(phase) && Readiness.Contains(readiness)
                && classification is "fixture" or "community" or "maintainer-supported" or "unknown"
                && roles.All(role => role is "metadata-authority" or "artifact-authority" or "identity-scheme"));
    }

    private static ConsumerCapability Capability(JsonElement capability)
    {
        Object(capability, "id", "version", "operationId", "owners", "dependencies", "support",
            "evidenceScope", "evidenceIds", "availability", "reasons", "omittedReasonCount");
        var owners = Ids(capability, "owners", 32);
        if (owners.IsEmpty) { throw new IncompatibleException(); }
        var support = Text(capability, "support", 128);
        var scope = Text(capability, "evidenceScope", 128);
        var availability = Text(capability, "availability", 128);
        var evidence = Ids(capability, "evidenceIds", 32);
        var reasons = ReadReasons(capability);
        return new(Id(capability, "id"), Version(capability, "version"), Id(capability, "operationId"), owners,
            Ids(capability, "dependencies", 32), support, scope, evidence, availability, reasons,
            Nonnegative(capability, "omittedReasonCount") == 0
                && support is "supported" or "unsupported" or "unverified" && scope is "fixture" or "production" or "unknown"
                && availability is "usable" or "unavailable" or "unknown"
                && (support != "supported" || scope != "unknown" && !evidence.IsEmpty));
    }

    private static ImmutableArray<ConsumerReason> ReadReasons(JsonElement owner)
    {
        Nonnegative(owner, "omittedReasonCount");
        return Array(owner, "reasons", 100).Select(reason =>
        {
            Object(reason, "code", "correctiveAction");
            var code = Text(reason, "code", 128);
            var action = Text(reason, "correctiveAction", 256);
            if (reason.TryGetProperty("moduleId", out _)) { Id(reason, "moduleId"); }
            if (reason.TryGetProperty("operationId", out _)) { Id(reason, "operationId"); }
            if (reason.TryGetProperty("correlationId", out _)
                && !Guid.TryParseExact(Text(reason, "correlationId", 36), "D", out _)) { throw new IncompatibleException(); }
            return Reasons.Contains(code) ? new ConsumerReason(code, action)
                : new ConsumerReason("observation-unknown", PresentationText.Unknown);
        }).ToImmutableArray();
    }

    private static void Object(JsonElement value, params string[] required)
    {
        if (value.ValueKind != JsonValueKind.Object) { throw new IncompatibleException(); }
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject())
        { if (!names.Add(property.Name)) { throw new IncompatibleException(); } }
        if (required.Any(name => !names.Contains(name))) { throw new IncompatibleException(); }
    }
    private static JsonElement.ArrayEnumerator Array(JsonElement owner, string key, int limit)
    {
        if (!owner.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Array || value.GetArrayLength() > limit)
        { throw new IncompatibleException(); }
        return value.EnumerateArray();
    }
    private static string Text(JsonElement owner, string key, int limit)
    {
        if (!owner.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        { throw new IncompatibleException(); }
        var text = value.GetString()!;
        if (text.Length > limit || text.Any(character => char.IsControl(character) || character is '<' or '>'))
        { throw new IncompatibleException(); }
        return text;
    }
    private static void OptionalText(JsonElement owner, string key, int limit)
    { if (owner.TryGetProperty(key, out _)) { Text(owner, key, limit); } }
    private static string Id(JsonElement owner, string key)
    {
        var value = Text(owner, key, 128);
        if (!Regex.IsMatch(value, "\\A[a-z0-9]+([.-][a-z0-9]+)*\\z", RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1)))
        { throw new IncompatibleException(); }
        return value;
    }
    private static string Version(JsonElement owner, string key)
    {
        var value = Text(owner, key, 128);
        if (!Regex.IsMatch(value, "\\A[0-9]+\\.[0-9]+\\.[0-9]+(?:[-+][a-zA-Z0-9.+-]+)?\\z",
            RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))) { throw new IncompatibleException(); }
        return value;
    }
    private static bool Bool(JsonElement owner, string key)
    {
        if (!owner.TryGetProperty(key, out var value) || value.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
        { throw new IncompatibleException(); }
        return value.GetBoolean();
    }
    private static int Nonnegative(JsonElement owner, string key)
    {
        if (!owner.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Number
            || !value.TryGetInt32(out var number) || number < 0) { throw new IncompatibleException(); }
        return number;
    }
    private static DateTimeOffset Date(JsonElement owner, string key)
    {
        if (!DateTimeOffset.TryParse(Text(owner, key, 40), CultureInfo.InvariantCulture,
            DateTimeStyles.RoundtripKind, out var value)) { throw new IncompatibleException(); }
        return value;
    }
    private static ImmutableArray<string> Strings(JsonElement owner, string key, int limit, int length)
    {
        var values = Array(owner, key, limit).Select(item =>
        {
            if (item.ValueKind != JsonValueKind.String) { throw new IncompatibleException(); }
            var value = item.GetString()!;
            if (value.Length > length || value.Any(character => char.IsControl(character) || character is '<' or '>'))
            { throw new IncompatibleException(); }
            return value;
        }).ToImmutableArray();
        if (values.Distinct().Count() != values.Length) { throw new IncompatibleException(); }
        return values;
    }
    private static ImmutableArray<string> Ids(JsonElement owner, string key, int limit)
    {
        var values = Strings(owner, key, limit, 128);
        if (values.Any(value => !Regex.IsMatch(value, "\\A[a-z0-9]+([.-][a-z0-9]+)*\\z",
            RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1)))) { throw new IncompatibleException(); }
        return values;
    }
}
