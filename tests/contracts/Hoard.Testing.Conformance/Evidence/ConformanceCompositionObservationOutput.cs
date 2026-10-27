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
    private static readonly ImmutableHashSet<string> OwnershipNames =
        ["callbackSettled", "workCompleted", "workFaulted", "ready", "admission", "unsafeActivities",
         "rootDisposal", "stopComplete", "initializations", "assessments", "workers", "stops", "disposals"];
    private static readonly ImmutableHashSet<string> AdmissionNames =
        ["ready", "admission", "phaseFailures", "fallbackRoots", "workers",
         "stopComplete", "rootDisposal", "unsafeActivities"];

    public static ImmutableArray<string> Render(ConformanceOriginalObservation source, string stage,
        IReadOnlyDictionary<string, int> counters)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(counters);
        var names = stage switch
        {
            "before-initialization" or "ready" or "stopped" => Names,
            "caller-cancelled" or "ownership-retained" or "ownership-settled" or "ownership-stopped"
                or "initialization-denied" => OwnershipNames,
            "admission-denied" or "denial-stopped" or "repair-admitted" or "repair-stopped" => AdmissionNames,
            _ => throw new ArgumentException("ProofMismatch")
        };
        if (source.Kind != "original-owner")
        { throw new ArgumentException("ProofMismatch"); }
        var copied = counters.ToImmutableDictionary(StringComparer.Ordinal);
        if (!names.SetEquals(copied.Keys) || copied.Values.Any(value => value is < 0 or > 1_000_000))
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
