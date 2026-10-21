using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryInventoryTests
{
    [Theory]
    [InlineData("complete")]
    [InlineData("partial")]
    public async Task Inclusion_registration_selection_and_roles_are_independent(string completeness)
    {
        LifecycleFixtures.Reset();
        var included = LifecycleFixtures.Declaration("included", ModuleCategory.Protocol);
        var builder = LifecycleFixtures.Registry();
        builder.AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity));
        builder.AddHoardDiscovery(new("fixture", "0.1.0", completeness) { IncludedModules = [included] }, new());
        var validation = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        await using var lease = await builder.ComposeHoardModulesAsync(validation.Composition!);
        var result = lease.Discovery!.Capture();
        Assert.True(result.Success);
        var observation = result.Observation!;
        Assert.Equal(completeness, observation.InventoryCompleteness);
        Assert.Equal(new[] { "artifact", "identity", "included", "metadata" }, observation.Modules.Select(module => module.Id));
        var unregistered = Assert.Single(observation.Modules, module => module.Id == "included");
        Assert.False(unregistered.Registered);
        Assert.False(unregistered.Enabled);
        Assert.Equal("unknown", unregistered.Readiness);
        var disabled = Assert.Single(observation.Modules, module => module.Id == "identity");
        Assert.True(disabled.Registered);
        Assert.False(disabled.Enabled);
        Assert.Equal("disabled", disabled.Readiness);
        Assert.DoesNotContain("identity", LifecycleFixtures.Controls.Keys);
        Assert.Equal("metadata-authority", Assert.Single(observation.Modules.Single(module => module.Id == "metadata").SelectedRoles));
        Assert.Equal("artifact-authority", Assert.Single(observation.Modules.Single(module => module.Id == "artifact").SelectedRoles));
        Assert.DoesNotContain(observation.Modules, module => module.Id == "absent");
    }

    [Fact]
    public async Task All_families_and_multiple_protocol_identity_selections_are_preserved_without_settings()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol))
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
            .AddModule<ConfiguredFixtures.SecondProtocol>(LifecycleFixtures.Declaration("protocol-two", ModuleCategory.Protocol))
            .AddModuleLifecycle<ConfiguredFixtures.SecondProtocol, ConfiguredFixtures.SecondProtocolModule>()
            .AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity))
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>()
            .AddModule<ConfiguredFixtures.SecondIdentity>(LifecycleFixtures.Declaration("identity-two", ModuleCategory.Identity))
            .AddModuleLifecycle<ConfiguredFixtures.SecondIdentity, ConfiguredFixtures.SecondIdentityModule>()
            .AddHoardDiscovery(new("fixture", "0.1.0", "partial"), new());
        var validated = builder.ValidateComposition(LifecycleFixtures.Selection("protocol", "protocol-two", "identity", "identity-two"),
            LifecycleFixtures.Versions, new());
        await using var lease = await builder.ComposeHoardModulesAsync(validated.Composition!);
        var modules = lease.Discovery!.Capture().Observation!.Modules;
        Assert.Equal(4, modules.Select(module => module.Category).Distinct().Count());
        Assert.Equal(2, modules.Count(module => module.Category == "protocol" && module.Enabled));
        Assert.Equal(2, modules.Count(module => module.Category == "identity" && module.Enabled && module.SelectedRoles.SequenceEqual(["identity-scheme"])));
        Assert.All(modules, module => Assert.True(module.Registered));
    }
}
