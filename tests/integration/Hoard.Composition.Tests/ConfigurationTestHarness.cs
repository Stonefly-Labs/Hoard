using System.Collections.Concurrent;
using System.Diagnostics.Metrics;
using System.Text;

namespace Hoard.Composition.Tests;

internal sealed class ConfigurationTestHarness : IAsyncDisposable
{
    internal const string Credential = "invented-configuration-credential";
    internal const string Locator = "INVENTED_CONFIGURATION_SECRET";
    private readonly LifecycleTestHarness lifecycle = new();
    private readonly MeterListener listener = new();
    private readonly ConcurrentQueue<string> measurements = new();
    private readonly string directory;

    internal ConfigurationTestHarness()
    {
        directory = Path.Combine(Path.GetTempPath(), $"hoard-configuration-test-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        if (!OperatingSystem.IsWindows())
        { System.IO.File.SetUnixFileMode(directory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
        listener.InstrumentPublished = (instrument, owner) =>
        {
            if (instrument.Meter.Name == "Hoard.Configuration") { owner.EnableMeasurementEvents(instrument); }
        };
        listener.SetMeasurementEventCallback<long>((instrument, value, tags, _) =>
        {
            measurements.Enqueue(instrument.Name);
            foreach (var tag in tags) { measurements.Enqueue($"{tag.Key}={tag.Value}"); }
        });
        listener.Start();
    }

    internal Dictionary<string, string> Environment { get; } = new(StringComparer.Ordinal)
    { [Locator] = Credential };
    internal string[] Output => [.. lifecycle.Logs, .. measurements];
    internal (long Sequence, string Id, string Phase)[] Events => lifecycle.Events;
    internal void Record(string owner, string phase) => lifecycle.Record(owner, phase);
    internal TaskCompletionSource Barrier() => lifecycle.Barrier();
    internal void Observe(Task task) => lifecycle.Observe(task);
    internal static Task Until(Func<bool> predicate) => LifecycleTestHarness.Until(predicate);
    internal string File(string name, string content)
    {
        var path = Path.Combine(directory, name);
        System.IO.File.WriteAllText(path, content, new UTF8Encoding(false, true));
        if (!OperatingSystem.IsWindows())
        { System.IO.File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite); }
        return path;
    }
    internal void AssertNoPayload(params string[] additional)
    {
        var output = string.Join("\n", Output);
        foreach (var payload in new[] { Credential, Locator }.Concat(additional))
        { Assert.DoesNotContain(payload, output); }
    }
    public async ValueTask DisposeAsync()
    {
        await lifecycle.DisposeAsync();
        listener.Dispose();
        foreach (var file in Directory.GetFiles(directory)) { System.IO.File.Delete(file); }
        Directory.Delete(directory);
    }
}
