using System.Text.Json.Nodes;
using Hoard.Discovery.ReferenceConsumer;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryConsumerRefreshTests
{
    internal sealed class Clock : TimeProvider
    {
        private long ticks;
        public override long TimestampFrequency => TimeSpan.TicksPerSecond;
        public override long GetTimestamp() => Interlocked.Read(ref ticks);
        public override DateTimeOffset GetUtcNow() => DateTimeOffset.UnixEpoch + TimeSpan.FromTicks(GetTimestamp());
        internal void Advance(TimeSpan duration) => Interlocked.Add(ref ticks, duration.Ticks);
    }

    [Fact]
    public async Task Generations_denial_failure_and_monotonic_age_never_revive_retained_actions()
    {
        var body = await DiscoveryPresentationTests.Body();
        var clock = new Clock();
        var state = new RefreshState(clock);
        Assert.Equal("loading", state.State);
        var first = state.Begin();
        var second = state.Begin();
        Assert.False(state.Complete(first, 200, body));
        Assert.True(state.Complete(second, 200, body));
        Assert.True(state.Current);
        clock.Advance(TimeSpan.FromSeconds(30));
        Assert.True(state.Current);
        clock.Advance(TimeSpan.FromTicks(1));
        Assert.Equal("stale", state.State);
        var refreshing = state.Begin();
        Assert.Equal("refreshing", state.State);
        Assert.False(state.Current);
        Assert.False(state.Complete(refreshing, 503, ReadOnlyMemory<byte>.Empty));
        Assert.Equal("stale", state.State);
        Assert.NotNull(state.Observation);
        Assert.True(state.Complete(state.Begin(), 200, body));
        var retained = state.Observation;
        var older = JsonNode.Parse(body)!;
        older["observation"]!["revision"] = "1";
        Assert.False(state.Complete(state.Begin(), 200, DiscoveryPresentationTests.Bytes(older)));
        Assert.Same(retained, state.Observation);
        Assert.False(state.Complete(state.Begin(), 403, ReadOnlyMemory<byte>.Empty));
        Assert.Equal("denied", state.State);
        Assert.Null(state.Observation);
        var replacement = JsonNode.Parse(body)!;
        replacement["observation"]!["lifecycleId"] = Guid.NewGuid().ToString();
        var latest = state.Begin();
        Assert.True(state.Complete(latest, 200, DiscoveryPresentationTests.Bytes(replacement)));
        Assert.False(state.Complete(latest, 200, body));
        Assert.False(state.Complete(latest - 1, 200, body));
        Assert.NotEqual(retained!.LifecycleId, state.Observation!.LifecycleId);
        Assert.True(DiscoveryJsonReader.CompareRevision("99999999999999999999", "10000000000000000000") > 0);
    }

    [Fact]
    public async Task Actual_denial_and_problem_bytes_have_distinct_error_denied_stale_and_empty_states()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture();
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            var state = new RefreshState();
            using var denied = await client.GetAsync("/api/v1/discovery");
            Assert.False(state.Complete(state.Begin(), (int)denied.StatusCode, await denied.Content.ReadAsByteArrayAsync()));
            Assert.Equal("denied", state.State);
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            using var invalid = await client.GetAsync("/api/v1/discovery?unsupported=value");
            Assert.False(state.Complete(state.Begin(), (int)invalid.StatusCode, await invalid.Content.ReadAsByteArrayAsync()));
            Assert.Equal("error", state.State);
            var body = await client.GetByteArrayAsync("/api/v1/discovery");
            Assert.True(state.Complete(state.Begin(), 200, body));
            Assert.False(state.Complete(state.Begin(), (int)invalid.StatusCode, await invalid.Content.ReadAsByteArrayAsync()));
            Assert.Equal("stale", state.State);
            var empty = JsonNode.Parse(body)!;
            empty["modules"] = new JsonArray();
            Assert.True(state.Complete(state.Begin(), 200, DiscoveryPresentationTests.Bytes(empty)));
            Assert.Equal("empty", state.State);
            Assert.Empty(PresentationProjector.Project(state.Observation!, state.Current, new HashSet<string>()));
        }
    }
}
