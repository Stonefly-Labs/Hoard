using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryLifecycleTests
{
    [Fact]
    public async Task Explicit_reassessment_updates_one_observation_without_refresh_probes_or_runtime_drain()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var ready = true;
        LifecycleFixtures.For("protocol").Readiness = _ => Task.FromResult(new HoardModuleReadiness(ready, []));
        var (app, lease) = await DiscoveryFixtures.Build();
        await using (lease)
        {
            await app.StartAsync();
            var initial = lease.Discovery!.Capture().Observation!;
            Assert.Equal("assessing-readiness", initial.Modules.Single(module => module.Id == "protocol").LifecyclePhase);
            Assert.NotNull(initial.ReadinessAssessedAt);
            ready = false;
            await lease.Lifecycle.AssessReadinessAsync();
            var lost = lease.Discovery.Capture().Observation!;
            Assert.False(lost.Ready);
            Assert.True(lost.StartupAdmission);
            Assert.Equal("unavailable", DiscoveryFixtures.Capability(lease.Discovery).Availability);
            var probes = LifecycleFixtures.For("protocol").Calls.Count(call => call == "readiness");
            for (var index = 0; index < 50; index++) { Assert.True(lease.Discovery.Capture().Success); }
            Assert.Equal(probes, LifecycleFixtures.For("protocol").Calls.Count(call => call == "readiness"));
            using var client = app.GetTestClient();
            Assert.Equal("fixture-operation", await client.GetStringAsync("/fixture-inspect"));
            ready = true;
            await lease.Lifecycle.AssessReadinessAsync();
            Assert.Equal("usable", DiscoveryFixtures.Capability(lease.Discovery).Availability);
            await lease.Lifecycle.StopAsync();
            Assert.Equal("unavailable", DiscoveryFixtures.Capability(lease.Discovery).Availability);
            Assert.All(lease.Discovery.Capture().Observation!.Modules.Where(module => module.Enabled),
                module => Assert.Equal("stopped", module.Readiness));
        }
    }

    [Fact]
    public async Task Failed_start_and_late_unknown_diagnostics_preserve_only_safe_terminal_reports()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        LifecycleFixtures.For("protocol").Initialize = _ => throw new InvalidOperationException(DiscoveryTestHarness.Secret);
        var (app, lease) = await DiscoveryFixtures.Build();
        await using (lease)
        {
            await Assert.ThrowsAsync<HoardLifecycleException>(() => app.StartAsync());
            var stopped = lease.Discovery!.Capture().Observation!;
            Assert.Equal("stopped", stopped.Phase);
            Assert.False(stopped.StartupAdmission);
            Assert.NotEmpty(lease.Lifecycle.Snapshot.Diagnostics);
            var coordinator = (HoardLifecycleCoordinator)lease.Lifecycle;
            for (var index = 0; index < 110; index++)
            { coordinator.Error(DiscoveryTestHarness.Locator, "unapproved-identity", HoardLifecyclePhase.Stopped); }
            var late = lease.Discovery.Capture().Observation!;
            Assert.True(late.Revision > stopped.Revision);
            Assert.Equal(100, late.Reasons.Length);
            Assert.True(late.OmittedReasonCount > 0);
            Assert.Contains(late.Reasons, reason => reason.Code == "observation-unavailable" && reason.ModuleId is null);
            var json = System.Text.Json.JsonSerializer.Serialize(late);
            Assert.DoesNotContain(DiscoveryTestHarness.Secret, json);
            Assert.DoesNotContain(DiscoveryTestHarness.Locator, json);
            Assert.DoesNotContain("unapproved-identity", json);
            Assert.DoesNotContain(late.Modules.SelectMany(module => module.Capabilities), capability => capability.Availability == "usable");
        }
    }
}
