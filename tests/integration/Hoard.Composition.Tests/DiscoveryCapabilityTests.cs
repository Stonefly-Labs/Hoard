using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryCapabilityTests
{
    [Theory]
    [InlineData("supported", "usable")]
    [InlineData("unsupported", "unavailable")]
    [InlineData("unverified", "unknown")]
    public async Task Exact_fixture_support_and_real_owned_route_are_required(string support, string availability)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryFixtures.Build(DiscoveryFixtures.Catalog(support));
        await using (lease)
        {
            await app.StartAsync();
            var capability = DiscoveryFixtures.Capability(lease.Discovery!);
            Assert.Equal(support, capability.Support);
            Assert.Equal(availability, capability.Availability);
            Assert.Equal(support == "supported" ? "fixture" : "unknown", capability.EvidenceScope);
            using var client = app.GetTestClient();
            Assert.Equal("fixture-operation", await client.GetStringAsync("/fixture-inspect"));
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Service_proof_does_not_resolve_and_shadowing_does_not_supply_owner_evidence(bool shadow)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        DiscoveryFixtures.InspectionService.Constructors = DiscoveryFixtures.InspectionService.Calls = 0;
        LifecycleFixtures.For("protocol").Configure = services => services.AddSingleton<DiscoveryFixtures.InspectionService>();
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        var builder = DiscoveryFixtures.Registry(web.Services, DiscoveryFixtures.Catalog(service: true),
            new() { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!;
        var lease = await builder.ComposeHoardModulesAsync(composition);
        await using (lease)
        {
            if (shadow) { web.Services.AddSingleton<DiscoveryFixtures.InspectionService>(); }
            var app = await web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            await app.StartAsync();
            Assert.Equal(shadow ? "unavailable" : "usable", DiscoveryFixtures.Capability(lease.Discovery!).Availability);
            Assert.Equal(0, DiscoveryFixtures.InspectionService.Constructors);
            app.Services.GetRequiredService<DiscoveryFixtures.InspectionService>().Inspect();
            Assert.Equal(1, DiscoveryFixtures.InspectionService.Constructors);
            Assert.Equal(1, DiscoveryFixtures.InspectionService.Calls);
        }
    }

    [Fact]
    public async Task Version_operation_and_multi_owner_scopes_remain_independent_of_unrelated_readiness()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var contributorReady = true;
        LifecycleFixtures.For("identity").Readiness = _ => Task.FromResult(new HoardModuleReadiness(contributorReady, []));
        LifecycleFixtures.For("artifact").Map = routes => routes.Map("inspect", "/artifact-inspect", ["GET"], _ => Task.CompletedTask);
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        static CapabilityDeclaration Capability(string version) => new() { Id = "inspect", Version = version, Description = "Fixture" };
        var builder = web.Services.AddHoard()
            .AddModule<LifecycleFixtures.MetadataProvider>(LifecycleFixtures.Declaration("metadata", ModuleCategory.Metadata))
            .AddModuleLifecycle<LifecycleFixtures.MetadataProvider, LifecycleFixtures.MetadataModule>()
            .AddModule<LifecycleFixtures.ArtifactProvider>(LifecycleFixtures.Declaration("artifact", ModuleCategory.Artifact) with
            { Capabilities = [Capability("0.2.0")], Endpoints = [new() { Id = "inspect", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ArtifactProvider, LifecycleFixtures.ArtifactModule>()
            .AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity) with
            { Capabilities = [Capability("0.1.0")] })
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            { Capabilities = [Capability("0.1.0")], Endpoints = [new() { Id = "inspect", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var first = DiscoveryFixtures.Catalog().Contributions[0];
        builder.AddHoardDiscovery(DiscoveryFixtures.Catalog() with
        {
            Contributions = [first, first with { Version = "0.2.0", Owners = ["artifact"], Routes = [new("artifact", "inspect", "POST")] },
                first with { OperationId = "joint", Owners = ["protocol", "identity"] }]
        }, new() { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection("protocol", "identity"), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(composition);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var initial = lease.Discovery!.Capture().Observation!;
        var operations = initial.Modules.SelectMany(module => module.Capabilities).ToArray();
        Assert.Equal(3, operations.Length);
        Assert.Equal("usable", operations.Single(item => item.OperationId == "inspect" && item.Version == "0.1.0").Availability);
        Assert.Equal("unavailable", operations.Single(item => item.Version == "0.2.0").Availability);
        var joint = initial.Modules.Single(module => module.Id == "identity").Capabilities.Single();
        Assert.Equal("joint", joint.OperationId);
        Assert.Equal(new[] { "identity", "protocol" }, joint.Owners);
        contributorReady = false;
        await lease.Lifecycle.AssessReadinessAsync();
        var lost = lease.Discovery.Capture().Observation!;
        Assert.False(lost.Ready);
        Assert.Equal("usable", lost.Modules.Single(module => module.Id == "protocol").Capabilities.Single(item => item.Version == "0.1.0").Availability);
        Assert.Equal("unavailable", lost.Modules.Single(module => module.Id == "identity").Capabilities.Single().Availability);
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task Optional_absence_removes_only_the_integration_and_enabled_incompatibility_still_rejects(bool registered, bool enabled)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        var builder = LifecycleFixtures.Registry(web.Services);
        if (registered)
        {
            builder.AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity) with { Version = "0.2.0" })
                .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>();
        }
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Capabilities = [new() { Id = "inspect", Version = "0.1.0", Description = "Fixture" }],
            Endpoints = [new() { Id = "inspect", Description = "Fixture" }],
            Dependencies = [new() { ModuleId = "identity", VersionRange = "[0.1.0,0.2.0)", Optional = true, AllowPrerelease = false }]
        }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var direct = DiscoveryFixtures.Catalog().Contributions[0];
        builder.AddHoardDiscovery(DiscoveryFixtures.Catalog() with
        { Contributions = [direct, direct with { OperationId = "integration", Dependencies = ["identity"] }] },
            new() { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        var selection = LifecycleFixtures.Selection("protocol") with
        { EnabledModuleIds = enabled ? ["metadata", "artifact", "protocol", "identity"] : ["metadata", "artifact", "protocol"] };
        var validation = builder.ValidateComposition(selection, LifecycleFixtures.Versions, new());
        if (enabled)
        {
            Assert.Null(validation.Composition);
            Assert.NotEmpty(validation.Diagnostics);
            Assert.All(LifecycleFixtures.Controls.Values, control => { Assert.Equal(0, control.Constructors); Assert.Empty(control.Calls); });
            return;
        }
        await using var lease = await builder.ComposeHoardModulesAsync(validation.Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var capabilities = lease.Discovery!.Capture().Observation!.Modules.Single(module => module.Id == "protocol").Capabilities;
        Assert.Equal("usable", capabilities.Single(item => item.OperationId == "inspect").Availability);
        Assert.Equal("unavailable", capabilities.Single(item => item.OperationId == "integration").Availability);
        Assert.DoesNotContain("identity", LifecycleFixtures.Controls.Keys);
    }
}
