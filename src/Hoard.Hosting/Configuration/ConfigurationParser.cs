using System.Collections.Immutable;
using System.Text;
using System.Text.Json;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Configuration;

internal sealed class ConfigurationParser(ImmutableDictionary<string, ConfigurationRegistration> metadata,
    HoardConfigurationOptions limits, ConfigurationSupervisor supervisor, HoardConfigurationSource source)
{
    private readonly Dictionary<string, SourceAssignment> assignments = new(StringComparer.Ordinal);
    private string failureOwner = "configuration";
    private string failureSetting = "unknown-setting";
    private static readonly UTF8Encoding Utf8 = new(false, true);
    private static readonly HashSet<string> Roots = new(StringComparer.Ordinal)
    { "configurationversion", "enabledmodules", "metadatamodule", "artifactmodule", "identitymodules", "requiredcapabilities", "modules" };

    internal SourceAssignment[] Document(string text, bool overlay)
    {
        try
        {
            if (text is null) { Reject(HoardConfigurationRule.InvalidSource); }
            if (Utf8.GetByteCount(text) > limits.MaximumDocumentBytes) { Reject(HoardConfigurationRule.InputLimit); }
            using var document = JsonDocument.Parse(text, new() { MaxDepth = limits.MaximumDepth });
            var root = Object(document.RootElement);
            if (root.Keys.Any(key => !Roots.Contains(key))) { Reject(HoardConfigurationRule.UnknownSetting); }
            if (overlay)
            {
                if (root.ContainsKey("configurationversion")) { Reject(HoardConfigurationRule.UnsupportedVersion); }
            }
            else if (!root.TryGetValue("configurationversion", out var version) || version.ValueKind != JsonValueKind.Number
                || !version.TryGetInt64(out var number) || number != 1)
            { Reject(HoardConfigurationRule.UnsupportedVersion); }
            if (!overlay) { Add("configurationversion", 1L); }
            foreach (var (key, value) in root)
            {
                supervisor.Check();
                failureOwner = "configuration";
                failureSetting = key;
                if (key == "configurationversion") { continue; }
                if (key == "modules") { Modules(value); }
                else { Add(key, RootValue(key, value)); }
            }
            return assignments.Values.ToArray();
        }
        catch (Exception error) when (error is JsonException or DecoderFallbackException or ArgumentException)
        { Reject(HoardConfigurationRule.InvalidSource); throw; }
    }

    internal void CommandLine(string path, string json)
    {
        try
        {
            using var document = JsonDocument.Parse(json, new() { MaxDepth = limits.MaximumDepth });
            var parts = path.Split(':');
            for (var index = 0; index < parts.Length; index++)
            { parts[index] = ConfigurationNames.Canonical(parts[index]) ?? throw new ConfigurationFailure(HoardConfigurationRule.UnknownSetting); }
            var identity = string.Join(':', parts);
            if (parts.Length == 1 && Roots.Contains(parts[0]) && parts[0] is not ("modules" or "configurationversion"))
            {
                failureOwner = "configuration";
                failureSetting = parts[0];
                Add(identity, RootValue(parts[0], document.RootElement));
                return;
            }
            if (parts.Length is not (3 or 4) || parts[0] != "modules" || !metadata.ContainsKey(parts[1]))
            { Reject(HoardConfigurationRule.UnknownSetting); }
            if (parts.Length == 3 && parts[2] == "optionsversion")
            {
                failureOwner = parts[1];
                failureSetting = identity;
                Add(identity, Integer(document.RootElement));
                return;
            }
            if (parts.Length != 4 || parts[2] != "options") { Reject(HoardConfigurationRule.UnknownSetting); }
            Add(identity, Option(parts[1], parts[3], document.RootElement));
        }
        catch (Exception error) when (error is JsonException or ArgumentException)
        { Reject(HoardConfigurationRule.InvalidSource); }
    }
    internal SourceAssignment[] Assignments => assignments.Values.ToArray();

    private Dictionary<string, JsonElement> Object(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object) { Reject(HoardConfigurationRule.InvalidSource); }
        var result = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject())
        {
            supervisor.Check();
            if (result.Count >= limits.MaximumAssignments) { Reject(HoardConfigurationRule.InputLimit); }
            var name = ConfigurationNames.Canonical(property.Name);
            if (name is null) { Reject(HoardConfigurationRule.UnknownSetting); }
            if (!result.TryAdd(name, property.Value)) { Reject(HoardConfigurationRule.DuplicateSetting); }
        }
        return result;
    }
    private void Modules(JsonElement value)
    {
        foreach (var (owner, module) in Object(value))
        {
            if (!metadata.ContainsKey(owner)) { Reject(HoardConfigurationRule.UnknownSetting); }
            failureOwner = owner;
            failureSetting = "unknown-setting";
            foreach (var (key, field) in Object(module))
            {
                failureOwner = owner;
                failureSetting = $"modules:{owner}:{key}";
                if (key == "optionsversion") { Add($"modules:{owner}:optionsversion", Integer(field)); }
                else if (key == "options")
                {
                    var options = Object(field);
                    if (options.Count > limits.MaximumFieldsPerModule) { Reject(HoardConfigurationRule.InputLimit); }
                    foreach (var (name, option) in options)
                    { Add($"modules:{owner}:options:{name}", Option(owner, name, option)); }
                }
                else { Reject(HoardConfigurationRule.UnknownSetting); }
            }
        }
    }
    private object Option(string owner, string name, JsonElement value)
    {
        failureOwner = owner;
        failureSetting = "unknown-setting";
        var field = metadata[owner].Contract.Fields.SingleOrDefault(item => ConfigurationNames.Canonical(item.Key) == name);
        if (field is null) { Reject(HoardConfigurationRule.UnknownSetting); }
        failureSetting = $"modules:{owner}:options:{name}";
        switch (field.Type)
        {
            case HoardOptionType.Integer: return Integer(value);
            case HoardOptionType.Boolean:
                if (value.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) { Reject(HoardConfigurationRule.InvalidSource); }
                return value.GetBoolean();
            case HoardOptionType.String: return Text(value);
            case HoardOptionType.Address:
                var text = Text(value);
                if (text.Contains('?') || text.Contains('#') || Uri.TryCreate(text, UriKind.Absolute, out var address)
                    && address.UserInfo.Length != 0)
                { Reject(HoardConfigurationRule.InvalidOption); }
                return text;
            case HoardOptionType.Secret: return Reference(value);
            default: Reject(HoardConfigurationRule.InvalidConfigurationContract); return false;
        }
    }
    private SecretReference Reference(JsonElement value)
    {
        var reference = Object(value);
        if (reference.Count != 2 || !reference.ContainsKey("kind") || !reference.ContainsKey("target"))
        { Reject(HoardConfigurationRule.InvalidSecretReference); }
        var kind = Text(reference["kind"]);
        var target = Text(reference["target"]);
        if (kind is not ("env" or "file")) { Reject(HoardConfigurationRule.UnsupportedSecretKind); }
        if (kind == "env")
        {
            if (target.Length is < 1 or > 128 || !(char.IsAsciiLetter(target[0]) || target[0] == '_')
                || target.Any(character => !char.IsAsciiLetterOrDigit(character) && character != '_'))
            { Reject(HoardConfigurationRule.InvalidSecretReference); }
        }
        else if (!Path.IsPathFullyQualified(target) || target.Contains('\0') || target.Contains("${", StringComparison.Ordinal)
            || target.Contains("$(", StringComparison.Ordinal) || target.Contains('`'))
        { Reject(HoardConfigurationRule.InvalidSecretReference); }
        return new(kind, target);
    }
    private object RootValue(string key, JsonElement value) => key switch
    {
        "enabledmodules" or "identitymodules" => Selection(value),
        "metadatamodule" or "artifactmodule" => Text(value),
        "requiredcapabilities" => Capabilities(value),
        _ => throw new ConfigurationFailure(HoardConfigurationRule.UnknownSetting)
    };
    private string[] Selection(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Array) { Reject(HoardConfigurationRule.InvalidSource); }
        if (value.GetArrayLength() > limits.MaximumSelectionIds) { Reject(HoardConfigurationRule.InputLimit); }
        var result = value.EnumerateArray().Select(Text).ToArray();
        if (result.Distinct(StringComparer.Ordinal).Count() != result.Length) { Reject(HoardConfigurationRule.DuplicateSetting); }
        return result;
    }
    private HoardRequiredCapability[] Capabilities(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Array) { Reject(HoardConfigurationRule.InvalidSource); }
        if (value.GetArrayLength() > limits.MaximumSelectionIds) { Reject(HoardConfigurationRule.InputLimit); }
        var result = new List<HoardRequiredCapability>();
        var identities = new HashSet<(string, string)>();
        foreach (var entry in value.EnumerateArray())
        {
            var fields = Object(entry);
            if (fields.Count != 4 || !fields.ContainsKey("module") || !fields.ContainsKey("id")
                || !fields.ContainsKey("range") || !fields.ContainsKey("allowprerelease")
                || fields["allowprerelease"].ValueKind is not (JsonValueKind.True or JsonValueKind.False))
            { Reject(HoardConfigurationRule.InvalidSource); }
            var capability = new HoardRequiredCapability(Text(fields["module"]), Text(fields["id"]),
                Text(fields["range"]), fields["allowprerelease"].GetBoolean());
            if (!identities.Add((capability.ModuleId, capability.CapabilityId))) { Reject(HoardConfigurationRule.DuplicateSetting); }
            result.Add(capability);
        }
        return result.ToArray();
    }
    private string Text(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.String) { Reject(HoardConfigurationRule.InvalidSource); }
        var text = value.GetString()!;
        if (Utf8.GetByteCount(text) > limits.MaximumStringBytes) { Reject(HoardConfigurationRule.InputLimit); }
        return text;
    }
    private long Integer(JsonElement value)
    {
        long number = 0;
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt64(out number))
        { Reject(HoardConfigurationRule.InvalidSource); }
        return number;
    }
    private void Add(string identity, object value)
    {
        if (assignments.Count >= limits.MaximumAssignments) { Reject(HoardConfigurationRule.InputLimit); }
        if (!assignments.TryAdd(identity, new(identity, value, source))) { Reject(HoardConfigurationRule.DuplicateSetting); }
        supervisor.Known("configuration", [identity]);
    }
    [System.Diagnostics.CodeAnalysis.DoesNotReturn]
    private void Reject(HoardConfigurationRule rule) =>
        supervisor.Reject(rule, HoardConfigurationPhase.Structure, source, failureOwner, failureSetting);
}
