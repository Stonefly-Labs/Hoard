using Hoard.Application.Discovery;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryOwnershipTests
{
    [Fact]
    public async Task Binding_requires_the_exact_retained_app_and_owned_source()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture();
        await using (lease)
        {
            var expected = lease.BindHoardDiscovery(app);
            Assert.Same(expected, lease.BindHoardDiscovery(app));
            Assert.Same(expected, app.Services.GetRequiredService<IHoardDiscoverySource>());
            Assert.Throws<HoardDiscoverySetupException>(() => app.MapHoardDiscovery(lease));
            var foreign = LifecycleFixtures.WebBuilder().Build();
            await using (foreign)
            {
                var error = Assert.Throws<HoardLifecycleException>(() => lease.BindHoardDiscovery(foreign));
                Assert.Contains(error.Diagnostics, diagnostic => diagnostic.RuleCode == "StaleComposition");
            }
        }

    }

    private sealed class SubstituteSource(IHoardDiscoverySource source) : IHoardDiscoverySource
    {
        public HoardDiscoveryReadResult Capture(CancellationToken cancellationToken = default) => source.Capture(cancellationToken);
    }

    [Fact]
    public async Task Substituted_DI_source_and_late_mapping_are_rejected_without_a_new_container()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        var builder = DiscoveryFixtures.Registry(web.Services, options: new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        web.Services.AddSingleton<IHoardDiscoverySource>(new SubstituteSource(lease.Discovery!));
        var app = await web.BuildHoardApplicationAsync(lease);
        var error = Assert.Throws<HoardLifecycleException>(() => lease.BindHoardDiscovery(app));
        Assert.Contains(error.Diagnostics, diagnostic => diagnostic.RuleCode == "StaleComposition");
        await app.MapHoardModulesAsync(lease);
        Assert.Throws<HoardLifecycleException>(() => app.MapHoardDiscovery(lease));
    }
}
