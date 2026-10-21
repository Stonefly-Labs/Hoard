using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryServiceBindingTests
{
    [Theory]
    [InlineData("valid", "usable")]
    [InlineData("removed", "unavailable")]
    [InlineData("wrong-owner", "unavailable")]
    [InlineData("keyed", "unavailable")]
    [InlineData("shadowed", "unavailable")]
    public async Task Effective_service_proof_requires_the_single_unkeyed_owner_added_descriptor(string mutation, string expected)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        DiscoveryFixtures.InspectionService.Constructors = 0;
        LifecycleFixtures.For(mutation == "wrong-owner" ? "artifact" : "protocol").Configure = services =>
        {
            if (mutation == "keyed") { services.AddKeyedSingleton<DiscoveryFixtures.InspectionService>("fixture"); }
            else { services.AddSingleton<DiscoveryFixtures.InspectionService>(); }
        };
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        var builder = DiscoveryFixtures.Registry(web.Services, DiscoveryFixtures.Catalog(service: true), new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        var validated = builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new());
        await using var lease = await builder.ComposeHoardModulesAsync(validated.Composition!);
        if (mutation == "removed") { web.Services.RemoveAll<DiscoveryFixtures.InspectionService>(); }
        if (mutation == "shadowed") { web.Services.AddSingleton<DiscoveryFixtures.InspectionService>(); }
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        Assert.Equal(expected, DiscoveryFixtures.Capability(lease.Discovery!).Availability);
        Assert.Equal(0, DiscoveryFixtures.InspectionService.Constructors);
        if (mutation == "valid")
        {
            app.Services.GetRequiredService<DiscoveryFixtures.InspectionService>().Inspect();
            Assert.Equal(1, DiscoveryFixtures.InspectionService.Constructors);
        }
    }
}
