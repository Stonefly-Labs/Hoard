using System.Collections.Concurrent;
using System.Diagnostics.Metrics;

namespace Hoard.Composition.Tests;

internal sealed class DiscoveryTestHarness : IAsyncDisposable
{
    internal const string Secret = "invented-discovery-sensitive-value";
    internal const string Locator = "INVENTED_DISCOVERY_PRIVATE_LOCATOR";
    private readonly LifecycleTestHarness lifecycle = new();
    private readonly MeterListener listener = new();
    private readonly ConcurrentQueue<string> measurements = new();

    internal DiscoveryTestHarness()
    {
        listener.InstrumentPublished = (instrument, owner) =>
        {
            if (instrument.Meter.Name == "Hoard.Discovery") { owner.EnableMeasurementEvents(instrument); }
        };
        listener.SetMeasurementEventCallback<long>((instrument, _, tags, _) =>
        {
            measurements.Enqueue(instrument.Name);
            foreach (var tag in tags) { measurements.Enqueue($"{tag.Key}={tag.Value}"); }
        });
        listener.Start();
    }

    internal TaskCompletionSource Barrier() => lifecycle.Barrier();
    internal void Observe(Task task) => lifecycle.Observe(task);
    internal string[] Output => [.. lifecycle.Logs, .. measurements];
    internal void AssertNoPayload(params string[] extra)
    {
        var output = string.Join("\n", Output);
        foreach (var marker in new[] { Secret, Locator }.Concat(extra))
        { Assert.DoesNotContain(marker, output); }
    }

    public async ValueTask DisposeAsync()
    {
        await lifecycle.DisposeAsync();
        listener.Dispose();
    }
}
