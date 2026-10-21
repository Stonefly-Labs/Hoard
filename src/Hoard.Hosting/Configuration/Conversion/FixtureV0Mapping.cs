using System.Text;
using System.Text.Json;

namespace Hoard.Hosting.Configuration.Conversion;

internal static class FixtureV0Mapping
{
    internal static readonly (string Old, string Current)[] Roots =
    [
        ("enabled", "enabledmodules"), ("metadata", "metadatamodule"), ("artifact", "artifactmodule"),
        ("identities", "identitymodules"), ("capabilities", "requiredcapabilities"), ("providers", "modules")
    ];

    internal static string Convert(string source, HoardConfigurationOptions options)
    {
        try
        {
            using var document = JsonDocument.Parse(source, new() { MaxDepth = options.MaximumDepth });
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
            var fields = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
            foreach (var property in document.RootElement.EnumerateObject())
            {
                var key = ConfigurationNames.Canonical(property.Name);
                if (key is null || !fields.TryAdd(key, property.Value))
                { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
            }
            if (fields.Count != 7 || !fields.TryGetValue("configurationversion", out var version)
                || version.ValueKind != JsonValueKind.String || version.GetString() != "fixture-v0"
                || Roots.Any(pair => !fields.ContainsKey(pair.Old)))
            { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
            if (fields["providers"].ValueKind == JsonValueKind.Object)
            {
                foreach (var provider in fields["providers"].EnumerateObject())
                {
                    if (provider.Value.ValueKind != JsonValueKind.Object) { continue; }
                    foreach (var field in provider.Value.EnumerateObject())
                    {
                        if (ConfigurationNames.Canonical(field.Name) == "optionsversion"
                            && (field.Value.ValueKind != JsonValueKind.Number
                                || !field.Value.TryGetInt64(out var optionVersion) || optionVersion != 1))
                        { throw new ConfigurationFailure(HoardConfigurationRule.UnsupportedVersion); }
                    }
                }
            }
            using var buffer = new MemoryStream();
            using (var writer = new Utf8JsonWriter(buffer))
            {
                writer.WriteStartObject();
                writer.WriteNumber("configurationversion", 1);
                foreach (var pair in Roots)
                {
                    writer.WritePropertyName(pair.Current);
                    fields[pair.Old].WriteTo(writer);
                }
                writer.WriteEndObject();
            }
            return Encoding.UTF8.GetString(buffer.GetBuffer(), 0, (int)buffer.Length);
        }
        catch (JsonException) { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
    }
}
