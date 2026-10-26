using System.Collections.Immutable;
using System.Text.Json;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceCompositionObservationOutput
{
    public const string Prefix = "hoard-composition-v1";
    private static readonly ImmutableHashSet<string> Names =
        ["metadataSingletons", "artifactSingletons", "metadataReady", "artifactReady", "ready", "admission",
         "disabledRoots", "protocolRequests", "identityRequests", "stopComplete", "unsafeActivities"];

    public static ImmutableArray<string> Render(ConformanceOriginalObservation source, string stage,
        IReadOnlyDictionary<string, int> counters)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(counters);
        if (source.Kind != "original-owner"
            || stage is not ("before-initialization" or "ready" or "stopped"))
        { throw new ArgumentException("ProofMismatch"); }
        var copied = counters.ToImmutableDictionary(StringComparer.Ordinal);
        if (!Names.SetEquals(copied.Keys) || copied.Values.Any(value => value is < 0 or > 1_000_000))
        { throw new ArgumentException("ProofMismatch"); }
        var id = Guid.NewGuid();
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            observationId = id,
            sourceId = source.ObservationId,
            stage,
            counters = copied
        });
        return ConformanceEvidencePacket.Render(Prefix, id, bytes);
    }

    public static void Write(ITestOutputHelper output, ConformanceOriginalObservation source, string stage,
        IReadOnlyDictionary<string, int> counters)
    {
        ArgumentNullException.ThrowIfNull(output);
        foreach (var packet in Render(source, stage, counters)) { output.WriteLine(packet); }
    }
}
