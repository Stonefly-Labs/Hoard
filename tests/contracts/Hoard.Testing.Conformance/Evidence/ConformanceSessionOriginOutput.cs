using System.Collections.Immutable;
using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceSessionOriginOutput
{
    public const string Prefix = "hoard-origin-v1";
    private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private sealed record Component(Guid InstanceId, string AssemblySha256, Guid ModuleVersionId, string TypeSha256);

    public static ImmutableArray<string> Render(ConformanceSessionOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(origin);
        return ConformanceEvidencePacket.Render(Prefix, origin.SessionId, Serialize(origin));
    }

    public static byte[] Serialize(ConformanceSessionOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(origin);
        var components = Components(origin.Components);
        return JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            runId = origin.RunId,
            caseId = origin.CaseId,
            sessionId = origin.SessionId,
            parentSessionId = origin.ParentSessionId,
            factoryOperation = origin.FactoryOperation,
            descriptorSha256 = origin.DescriptorSha256,
            runtimeVersion = origin.RuntimeVersion,
            processArchitecture = origin.ProcessArchitecture,
            components
        }, Json);
    }

    public static byte[] Serialize(ConformanceArtifactRecoveryOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(origin);
        return JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = origin.SchemaVersion,
            kind = origin.Kind,
            runId = origin.RunId,
            caseId = origin.CaseId,
            sessionId = origin.SessionId,
            sourceSessionId = origin.SourceSessionId,
            recoveryInputSha256 = origin.RecoveryInputSha256,
            factoryOperation = origin.FactoryOperation,
            descriptorSha256 = origin.DescriptorSha256,
            runtimeVersion = origin.RuntimeVersion,
            processArchitecture = origin.ProcessArchitecture,
            components = Components(origin.Components)
        }, Json);
    }

    private static Dictionary<string, Component> Components(
        ImmutableSortedDictionary<string, ConformanceObservedComponent> components) =>
        components.ToDictionary(pair => pair.Key, pair => new Component(
            pair.Value.InstanceId, pair.Value.Assembly.AssemblySha256,
            pair.Value.Assembly.ModuleVersionId, pair.Value.Assembly.TypeSha256), StringComparer.Ordinal);
    public static void Write(ITestOutputHelper output, ConformanceSessionOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(output);
        foreach (var packet in Render(origin)) { output.WriteLine(packet); }
        if (origin.Components.ContainsKey("schema"))
        {
            foreach (var (role, component) in origin.ObservedObjects)
            {
                ConformanceMetadataArgumentOutput.Flush(output, origin.RunId, origin.CaseId,
                    "session-origin", origin.SessionId, role, component, origin.Components[role].InstanceId);
            }
        }
    }
}

internal static class ConformanceEvidencePacket
{
    internal static ImmutableArray<string> Render(string prefix, Guid id, byte[] bytes)
    {
        if (bytes.Length > 64 * 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var encoded = Convert.ToBase64String(bytes);
        var count = (encoded.Length + 511) / 512;
        var result = ImmutableArray.CreateBuilder<string>(count);
        for (var index = 0; index < count; index++)
        {
            var chunk = encoded.Substring(index * 512, Math.Min(512, encoded.Length - index * 512));
            result.Add(string.Create(CultureInfo.InvariantCulture,
                $"{prefix}:{id:D}:{index}:{count}:{digest}:{chunk}"));
        }
        return result.MoveToImmutable();
    }

}
