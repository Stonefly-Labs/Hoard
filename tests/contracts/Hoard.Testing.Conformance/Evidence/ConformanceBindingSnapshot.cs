using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceBindingSnapshot
{
    public static ImmutableArray<byte> Capture(ConformanceBindingDeclaration declaration)
    {
        ArgumentNullException.ThrowIfNull(declaration);
        ConformanceBindingAdmission.Validate(declaration, declaration.Category);
        using var output = new MemoryStream();
        using (var writer = new Utf8JsonWriter(output))
        {
            writer.WriteStartObject();
            writer.WriteNumber("schemaVersion", 1);
            writer.WriteString("bindingId", declaration.BindingId);
            writer.WriteString("category", declaration.Category.ToString().ToLowerInvariant());
            writer.WriteString("packageId", declaration.PackageId);
            writer.WriteString("packageVersion", declaration.PackageVersion);
            writer.WriteString("packageSha256", declaration.PackageSha256);
            writer.WriteStartArray("capabilities");
            foreach (var capability in declaration.Capabilities)
            {
                writer.WriteStringValue(capability);
            }
            writer.WriteEndArray();
            writer.WriteStartArray("faults");
            foreach (var fault in declaration.Faults)
            {
                writer.WriteStringValue(fault.ToString());
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        if (output.Length > 64 * 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
        return output.ToArray().ToImmutableArray();
    }
}
