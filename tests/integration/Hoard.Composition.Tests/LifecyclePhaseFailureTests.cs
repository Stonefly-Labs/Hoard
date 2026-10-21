using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.Logging;

namespace Hoard.Composition.Tests;

public class LifecyclePhaseFailureTests
{
    [Theory]
    [InlineData("services", false)]
    [InlineData("map", false)]
    [InlineData("initialize", false)]
    [InlineData("readiness", false)]
    [InlineData("services", true)]
    [InlineData("map", true)]
    [InlineData("initialize", true)]
    [InlineData("readiness", true)]
    public async Task Entered_failure_preserves_safe_primary_error_and_cleans_once(string phase, bool timeout)
    {
        LifecycleFixtures.Reset();
        await using var capture = new LifecycleTestHarness();
        var control = LifecycleFixtures.For("artifact");
        Exception Fault() => timeout ? new TimeoutException("seeded-secret") : new InvalidOperationException("seeded-secret");
        if (phase == "services") { control.Configure = _ => throw Fault(); }
        if (phase == "map") { control.Map = _ => throw Fault(); }
        if (phase == "initialize") { control.Initialize = _ => throw Fault(); }
        if (phase == "readiness") { control.Readiness = _ => throw Fault(); }
        var web = LifecycleFixtures.WebBuilder();
        web.Logging.AddProvider(capture);
        var builder = LifecycleFixtures.Registry(web.Services);
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        HoardLifecycleException error;
        if (phase == "services")
        { error = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(composition)); }
        else
        {
            var lease = await builder.ComposeHoardModulesAsync(composition);
            var app = await web.BuildHoardApplicationAsync(lease);
            if (phase == "map") { error = await Assert.ThrowsAsync<HoardLifecycleException>(() => app.MapHoardModulesAsync(lease)); }
            else
            {
                await app.MapHoardModulesAsync(lease);
                var result = await lease.Lifecycle.StartAsync();
                Assert.False(result.Ready);
                error = new HoardLifecycleException(result.Diagnostics);
            }
            await lease.DisposeAsync();
        }
        Assert.Null(error.InnerException);
        Assert.DoesNotContain("seeded-secret", error.ToString());
        Assert.DoesNotContain("seeded-secret", string.Join("\n", capture.Logs));
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        Assert.Single(error.Diagnostics, item => item.RuleCode == (timeout ? "Timeout" : phase == "readiness" ? "InvalidReadiness" : "PhaseFailure"));
        Assert.DoesNotContain(error.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
        Assert.DoesNotContain("worker", control.Calls);
        Assert.Equal(1, control.Calls.Count(item => item == "stop"));
    }

    [Fact]
    public async Task Throwing_constructor_self_cleans_without_returned_adapter_or_leaked_details()
    {
        LifecycleFixtures.Reset();
        ConstructorFailure.Acquired = ConstructorFailure.Released = 0;
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var existing = web.Services.Single(item => item.ImplementationInstance is HoardModuleLifecycleRegistration registration
            && registration.ProviderType == typeof(LifecycleFixtures.ArtifactProvider));
        web.Services.Remove(existing);
        builder.AddModuleLifecycle<LifecycleFixtures.ArtifactProvider, ConstructorFailure>();
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(composition));
        Assert.Contains(error.Diagnostics, item => item.RuleCode == "PhaseFailure");
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        Assert.DoesNotContain("constructor-secret", error.ToString());
        Assert.Equal(1, ConstructorFailure.Acquired);
        Assert.Equal(ConstructorFailure.Acquired, ConstructorFailure.Released);
        Assert.DoesNotContain("stop", LifecycleFixtures.For("artifact").Calls);
    }

    private sealed class ConstructorFailure : LifecycleFixtures.Module
    {
        internal static int Acquired;
        internal static int Released;
        public ConstructorFailure() : base("artifact")
        {
            Interlocked.Increment(ref Acquired);
            try { throw new InvalidOperationException("constructor-secret"); }
            finally { Interlocked.Increment(ref Released); }
        }
    }
}
