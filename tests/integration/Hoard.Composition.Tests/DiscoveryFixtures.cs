using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

internal static class DiscoveryFixtures
{
    internal static HoardDiscoveryCatalog Catalog(string support = "supported", bool service = false) =>
        new("discovery-fixture", "0.1.0", "complete")
        {
            Contributions = [new("inspect", "0.1.0", "inspect", ["protocol"])
            {
                Support = support,
                EvidenceScope = support == "supported" ? "fixture" : "unknown",
                EvidenceIds = support == "supported" ? ["fixture-inspect"] : [],
                Routes = service ? [] : [new("protocol", "inspect", "GET")],
                Services = service ? ["inspection-service"] : []
            }],
            ServiceBindings = service ? [new("inspection-service", "protocol", typeof(InspectionService))] : []
        };

    internal static HoardBuilder Registry(IServiceCollection? services = null,
        HoardDiscoveryCatalog? catalog = null, HoardDiscoveryOptions? options = null)
    {
        var builder = LifecycleFixtures.Registry(services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(
            LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            {
                Capabilities = [new() { Id = "inspect", Version = "0.1.0", Description = DiscoveryTestHarness.Secret }],
                Endpoints = [new() { Id = "inspect", Description = DiscoveryTestHarness.Secret }]
            }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        return builder.AddHoardDiscovery(catalog ?? Catalog(), options ?? new());
    }

    internal static async Task<(WebApplication App, HoardServiceComposition Lease)> Build(
        HoardDiscoveryCatalog? catalog = null, HoardDiscoveryOptions? options = null)
    {
        var web = LifecycleFixtures.WebBuilder();
        ConfigureExposure(web.Services);
        var builder = Registry(web.Services, catalog, options ?? new() { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        var validation = builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new());
        var lease = await builder.ComposeHoardModulesAsync(validation.Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        return (app, lease);
    }

    internal static DiscoveryCapability Capability(IHoardDiscoverySource source) =>
        Assert.Single(Assert.Single(source.Capture().Observation!.Modules, module => module.Id == "protocol").Capabilities);

    internal static void ConfigureExposure(IServiceCollection services)
    {
        services.AddAuthorization(authorization => authorization.AddPolicy("Hoard.Management.Read",
            policy => policy.RequireAssertion(_ => true)));
        services.AddSingleton<IDiscoveryExposureAdapter, DiscoveryAuthorizationTests.FixtureExposure>();
    }

    internal sealed class InspectionService
    {
        internal static int Constructors;
        internal static int Calls;
        public InspectionService() => Interlocked.Increment(ref Constructors);
        internal void Inspect() => Interlocked.Increment(ref Calls);
    }

    internal static void Map(bool actual = true)
    {
        LifecycleFixtures.For("protocol").Map = routes =>
        {
            if (actual) { routes.Map("inspect", "/fixture-inspect", ["GET"], context => context.Response.WriteAsync("fixture-operation")); }
        };
    }
}
