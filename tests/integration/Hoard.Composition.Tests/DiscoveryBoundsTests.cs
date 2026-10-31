using System.Collections.Immutable;
using System.Reflection;
using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Application.Discovery;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryBoundsTests
{
    private sealed class ProjectionClock : TimeProvider
    {
        internal Action? DuringProjection;
        private int calls;
        internal long Ticks;
        public override long TimestampFrequency => TimeSpan.TicksPerSecond;
        public override long GetTimestamp()
        {
            if (DuringProjection is not null && ++calls == 5) { DuringProjection(); }
            return Ticks;
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Cancellation_and_deadline_during_HTTP_projection_leave_live_modules_untouched(bool deadline)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var clock = new ProjectionClock();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture(options:
            new() { Exposure = HoardDiscoveryExposure.SecuredNetwork, TimeProvider = clock });
        await using (lease)
        {
            var workers = LifecycleFixtures.Controls.ToDictionary(pair => pair.Key,
                _ => new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously));
            foreach (var (id, entered) in workers)
            {
                LifecycleFixtures.For(id).Worker = _ => { entered.SetResult(); return Task.CompletedTask; };
            }
            await app.StartAsync();
            await Task.WhenAll(workers.Values.Select(entered => entered.Task)).WaitAsync(TimeSpan.FromSeconds(5));
            var before = LifecycleFixtures.Controls.ToDictionary(pair => pair.Key, pair => pair.Value.Calls.ToArray());
            using var cancellation = new CancellationTokenSource();
            clock.DuringProjection = () =>
            {
                if (deadline) { clock.Ticks += TimeSpan.FromSeconds(2).Ticks; }
                else { cancellation.Cancel(); }
            };
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            if (deadline)
            {
                using var response = await client.GetAsync("/api/v1/discovery", cancellation.Token);
                Assert.Equal(503, (int)response.StatusCode);
                using var problem = JsonDocument.Parse(await response.Content.ReadAsByteArrayAsync());
                Assert.Equal("deadline", problem.RootElement.GetProperty("code").GetString());
                Assert.Equal("capture", problem.RootElement.GetProperty("phase").GetString());
            }
            else
            {
                await Assert.ThrowsAnyAsync<OperationCanceledException>(() => client.GetAsync("/api/v1/discovery", cancellation.Token));
            }
            Assert.Equal(HoardLifecyclePhase.Running, lease.Lifecycle.Snapshot.Phase);
            Assert.True(lease.Lifecycle.Snapshot.StartupAdmission);
            foreach (var (id, calls) in before) { Assert.Equal(calls, LifecycleFixtures.For(id).Calls); }
            Assert.True(lease.Discovery!.Capture().Success);
        }
    }

    [Theory]
    [InlineData(4 * 1024 * 1024, 200)]
    [InlineData(4 * 1024 * 1024 + 1, 503)]
    public async Task Exact_encoded_byte_bound_is_checked_before_success_headers(int bytes, int status)
    {
        var context = new DefaultHttpContext();
        using var body = new MemoryStream();
        context.Response.Body = body;
        var options = new HoardDiscoveryOptions { Deadline = TimeSpan.FromSeconds(10) };
        var values = new List<string>();
        var remaining = bytes - 1;
        while (remaining > 259) { values.Add(new string('a', 256)); remaining -= 259; }
        values.Add(new string('a', remaining - 3));
        await DiscoveryResponseWriter.SendAsync(context, options, new(options, default),
            () => values, "/api/v1/discovery");
        Assert.Equal(status, context.Response.StatusCode);
        if (status == 200) { Assert.Equal(bytes, body.Length); }
        else
        {
            using var problem = JsonDocument.Parse(body.ToArray());
            Assert.Equal("response-limit", problem.RootElement.GetProperty("code").GetString());
            Assert.Equal("encoding", problem.RootElement.GetProperty("phase").GetString());
        }
    }

    [Fact]
    public async Task Escaped_UTF8_expansion_cannot_produce_a_partial_success()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var included = Enumerable.Range(0, 16).Select(index =>
            LifecycleFixtures.Declaration($"included-{index}", ModuleCategory.Protocol) with
            {
                Configuration = Enumerable.Range(0, 256).Select(field => new ConfigurationRequirement
                { Key = $"field-{field}", Description = "Not approved", Required = false, SecretReference = false }).ToImmutableArray()
            }).ToImmutableArray();
        var catalog = DiscoveryFixtures.Catalog() with
        {
            IncludedModules = included,
            Publications = included.Select(module => new DiscoveryPublicationPolicy(module.Id)
            {
                Options = module.Configuration.Select(field => new DiscoveryPublicOption(field.Key)
                { Description = new string('\u03bb', 512) }).ToImmutableArray()
            }).ToImmutableArray()
        };
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture(catalog,
            new() { Exposure = HoardDiscoveryExposure.SecuredNetwork, Deadline = TimeSpan.FromSeconds(10) });
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            using var response = await client.GetAsync("/api/v1/discovery");
            Assert.Equal(503, (int)response.StatusCode);
            using var problem = JsonDocument.Parse(await response.Content.ReadAsByteArrayAsync());
            Assert.Equal("response-limit", problem.RootElement.GetProperty("code").GetString());
            Assert.False(problem.RootElement.TryGetProperty("modules", out _));
        }
    }

    [Fact]
    public async Task Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture();
        await using (lease)
        {
            using var cancelled = new CancellationTokenSource();
            cancelled.Cancel();
            var result = lease.Discovery!.Capture(cancelled.Token);
            Assert.False(result.Success);
            Assert.Equal("cancelled", result.Failure!.Code);
            var field = typeof(DiscoveryLifecyclePublication).GetField("current", BindingFlags.Instance | BindingFlags.NonPublic)!;
            var publication = lease.Publication!;
            var saved = publication.Capture()!;
            field.SetValue(publication, saved with { LifecycleId = Guid.NewGuid() });
            Assert.Equal("observation-unavailable", lease.Discovery.Capture().Failure!.Code);
            field.SetValue(publication, null);
            Assert.Equal("observation-unavailable", lease.Discovery.Capture().Failure!.Code);
            field.SetValue(publication, saved);
            Assert.True(lease.Discovery.Capture().Success);
        }
        var context = new DefaultHttpContext();
        using var output = new MemoryStream();
        context.Response.Body = output;
        var clock = new DiscoveryConsumerRefreshTests.Clock();
        var options = new HoardDiscoveryOptions { TimeProvider = clock };
        var budget = new DiscoveryResponseWriter.Budget(options, default);
        clock.Advance(TimeSpan.FromSeconds(2));
        await DiscoveryResponseWriter.SendAsync(context, options, budget, () => "unused", "/api/v1/discovery");
        Assert.Equal(503, context.Response.StatusCode);
        Assert.Contains("deadline", System.Text.Encoding.UTF8.GetString(output.ToArray()), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Cancellation_during_encoding_releases_owned_buffers_without_disposing_provider_resources()
    {
        using var cancellation = new CancellationTokenSource();
        var context = new DefaultHttpContext { RequestAborted = cancellation.Token };
        using var output = new MemoryStream();
        context.Response.Body = output;
        var options = new HoardDiscoveryOptions();
        IEnumerable<string> DuringSerialization()
        {
            for (var index = 0; index < 1000; index++)
            {
                if (index == 100) { cancellation.Cancel(); }
                yield return new string('a', 512);
            }
        }
        await DiscoveryResponseWriter.SendAsync(context, options, new(options, cancellation.Token),
            DuringSerialization, "/api/v1/discovery");
        Assert.Empty(output.ToArray());
        Assert.False(context.Response.HasStarted);
    }

    [Fact]
    public async Task Deadline_during_actual_encoding_cannot_commit_a_partial_success()
    {
        var clock = new DiscoveryConsumerRefreshTests.Clock();
        var context = new DefaultHttpContext();
        using var output = new MemoryStream();
        context.Response.Body = output;
        var options = new HoardDiscoveryOptions { TimeProvider = clock };
        IEnumerable<string> DuringSerialization()
        {
            for (var index = 0; index < 1000; index++)
            {
                if (index == 100) { clock.Advance(TimeSpan.FromSeconds(2)); }
                yield return new string('a', 512);
            }
        }
        await DiscoveryResponseWriter.SendAsync(context, options, new(options, default),
            DuringSerialization, "/api/v1/discovery");
        Assert.Equal(503, context.Response.StatusCode);
        using var problem = JsonDocument.Parse(output.ToArray());
        Assert.Equal("deadline", problem.RootElement.GetProperty("code").GetString());
        Assert.Equal("encoding", problem.RootElement.GetProperty("phase").GetString());
    }

    [Fact]
    public async Task Encoding_rejects_oversized_tokens_before_uncapped_writer_allocation()
    {
        var payload = new string('a', 8 * 1024 * 1024);
        var context = new DefaultHttpContext();
        using var output = new MemoryStream();
        context.Response.Body = output;
        var options = new HoardDiscoveryOptions();
        var before = GC.GetAllocatedBytesForCurrentThread();
        await DiscoveryResponseWriter.SendAsync(context, options, new(options, default), () => payload, "/api/v1/discovery");
        var allocated = GC.GetAllocatedBytesForCurrentThread() - before;
        Assert.Equal(503, context.Response.StatusCode);
        Assert.InRange(allocated, 0, 8 * 1024 * 1024);
    }
}
