using System.Collections.Immutable;
using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceSessionOriginOutput
{
    public const string Prefix = "hoard-origin-v1";

    public static ImmutableArray<string> Render(ConformanceSessionOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(origin);
        var components = origin.Components.ToDictionary(pair => pair.Key, pair => new
        {
            instanceId = pair.Value.InstanceId,
            assemblySha256 = pair.Value.Assembly.AssemblySha256,
            moduleVersionId = pair.Value.Assembly.ModuleVersionId,
            typeSha256 = pair.Value.Assembly.TypeSha256
        }, StringComparer.Ordinal);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new
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
        });
        return ConformanceEvidencePacket.Render(Prefix, origin.SessionId, bytes);
    }

    public static void Write(ITestOutputHelper output, ConformanceSessionOrigin origin)
    {
        ArgumentNullException.ThrowIfNull(output);
        foreach (var packet in Render(origin)) { output.WriteLine(packet); }
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
