using System.Text.Json;
using Hoard.Discovery.ReferenceConsumer;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryRestartTests
{
    [Fact]
    public void Prepared_discovery_restart_journeys_have_distinct_lifecycles_and_actual_operations()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_DISCOVERY_EVIDENCE");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-discovery.sh to prepare actual package-only journeys.");
        using var document = JsonDocument.Parse(File.ReadAllText(path!));
        var journeys = document.RootElement.GetProperty("journeys").EnumerateArray().ToArray();
        Assert.Equal(9, journeys.Length);
        var successful = journeys.Where(journey => journey.GetProperty("id").GetString() != "invalid-replacement").ToArray();
        Assert.Equal(7, successful.Select(journey => journey.GetProperty("lifecycleId").GetString()).Distinct().Count());
        Assert.All(successful, journey =>
        {
            Assert.True(journey.GetProperty("passed").GetBoolean());
            Assert.Equal(1, journey.GetProperty("routeCalls").GetInt32());
            Assert.Equal(1, journey.GetProperty("serviceCalls").GetInt32());
            Assert.InRange(journey.GetProperty("bytes").GetInt32(), 1, 4 * 1024 * 1024);
        });
        var observations = document.RootElement.GetProperty("observations").EnumerateArray().ToArray();
        Assert.Equal(7, observations.Length);
        var state = new RefreshState();
        foreach (var observation in observations)
        {
            var bytes = System.Text.Encoding.UTF8.GetBytes(observation.GetRawText());
            Assert.True(DiscoveryJsonReader.Read(bytes).Compatible);
            var attempt = state.Begin();
            Assert.True(state.Complete(attempt, 200, bytes));
            Assert.False(state.Complete(attempt - 1, 200, bytes));
        }
    }
}
