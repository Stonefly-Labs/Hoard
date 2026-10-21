using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class CompositionSnapshotTests
{
    [Fact]
    public async Task Later_registry_mutation_or_another_builder_cannot_activate_validated_snapshot()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry();
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        builder.Services.AddSingleton("later");
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(composition));
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        await Assert.ThrowsAsync<HoardLifecycleException>(() => LifecycleFixtures.Registry().ComposeHoardModulesAsync(composition));
        Assert.Empty(LifecycleFixtures.Controls);
    }
}
