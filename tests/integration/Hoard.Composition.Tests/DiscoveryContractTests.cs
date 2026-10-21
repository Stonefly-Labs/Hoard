using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryContractTests
{
    [Fact]
    public void Catalog_is_frozen_before_composition_and_invalid_static_inputs_never_activate()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry();
        builder.AddHoardDiscovery(new("fixture-distribution", "0.1.0", "complete"), new());
        var validation = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        Assert.NotNull(validation.Composition);
        Assert.Throws<HoardDiscoverySetupException>(() =>
            builder.AddHoardDiscovery(new("other", "0.1.0", "partial"), new()));
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public void Nonpositive_deadline_rejects_before_construction(int milliseconds)
    {
        LifecycleFixtures.Reset();
        Assert.Throws<HoardDiscoverySetupException>(() => LifecycleFixtures.Registry()
            .AddHoardDiscovery(new("fixture", "0.1.0", "partial"),
                new() { Deadline = TimeSpan.FromMilliseconds(milliseconds) }));
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Discovery_free_composition_remains_opt_out()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry();
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(composition);
        Assert.Null(lease.Discovery);
    }
}
