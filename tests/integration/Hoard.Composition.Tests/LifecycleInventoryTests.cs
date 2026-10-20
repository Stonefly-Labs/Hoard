using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleInventoryTests
{
    [Fact]
    public async Task Registered_disabled_enabled_ready_and_stopped_remain_distinct_immutable_observations()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services)
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("disabled", ModuleCategory.Protocol));
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var original = lease.Lifecycle.Snapshot;
        Assert.False(original.Ready);
        Assert.Contains(original.Modules, module => module.ModuleId == "disabled" && module.IncludedByRegistration
            && !module.Enabled && module.Status == HoardModuleStatus.Disabled);
        Assert.All(original.Modules.Where(module => module.Enabled), module => Assert.Equal(HoardModuleStatus.Enabled, module.Status));
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        Assert.True(lease.Lifecycle.Snapshot.Ready);
        Assert.False(original.Ready);
        Assert.All(original.Modules.Where(module => module.Enabled), module => Assert.Equal(HoardModuleStatus.Enabled, module.Status));
        await app.StopHoardApplicationAsync(lease);
        Assert.False(lease.Lifecycle.Snapshot.Ready);
        Assert.Equal(HoardLifecyclePhase.Stopped, lease.Lifecycle.Snapshot.Phase);
    }
}
