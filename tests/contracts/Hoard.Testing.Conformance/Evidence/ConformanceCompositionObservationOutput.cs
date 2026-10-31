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
    private static readonly ImmutableHashSet<string> StoreAdmissionNames =
        ["ready", "admission", "phaseFailures", "fallbackEffects", "workers",
         "stopComplete", "rootDisposal", "unsafeActivities", "storeBeforeRoot", "storeAdmitted", "storeReady"];
    private static readonly ImmutableHashSet<string> RestartNames =
        ["ready", "admission", "stopComplete", "rootDisposal", "unsafeActivities", "workers", "inactiveEffects",
         "requests", "requestPending", "requestSettled", "configurationFixed", "identityChanged"];
    private static readonly ImmutableHashSet<string> MatrixNames =
        ["constructors", "services", "maps", "requests", "connections", "initializations", "assessments",
         "workers", "stops", "disposals", "disabledEffects", "ready", "admission", "stopComplete",
         "rootDisposal", "unsafeActivities", "ruleCount", "activeEdges", "satisfiedCapabilities", "publishedRoutes"];

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
            "store-denied" or "store-denial-stopped" or "store-repair-admitted" or "store-repair-stopped"
                => StoreAdmissionNames,
            "selection-fixed" or "selection-stopped" or "selection-restarted" or "configuration-active"
                or "configuration-draining" or "configuration-stopped" or "configuration-restarted"
                or "restart-draining" or "restart-stopped" => RestartNames,
            "declaration-rejected" or "declaration-ready" or "declaration-stopped"
                or "multiple-ready" or "multiple-stopped" or "mapping-rejected" or "mapping-denial-stopped"
                or "mapping-ready" or "mapping-stopped" or "optional-unavailable" or "optional-unavailable-stopped"
                or "optional-enabled" or "optional-enabled-stopped" => MatrixNames,
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
