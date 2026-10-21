using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleRestartTests
{
    [Fact]
    public async Task Invalid_replacement_does_not_roll_back_and_explicit_fresh_previous_selection_recovers()
    {
        LifecycleFixtures.Reset();
        var first = LifecycleFixtures.Registry();
        var firstSelection = LifecycleFixtures.Selection();
        var firstComposition = first.ValidateComposition(firstSelection, LifecycleFixtures.Versions, new()).Composition!;
        await using var firstLease = await first.ComposeHoardModulesAsync(firstComposition);
        firstSelection = firstSelection with { EnabledModuleIds = ["absent"] };
        Assert.Equal(new[] { "metadata", "artifact" }, firstComposition.EnabledModuleIds.ToArray());
        Assert.Null(LifecycleFixtures.Registry().ValidateComposition(firstSelection, LifecycleFixtures.Versions, new()).Composition);
        var previous = LifecycleFixtures.Registry();
        await using var restored = await previous.ComposeHoardModulesAsync(previous.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        Assert.NotEqual(firstLease.Lifecycle.Snapshot.CompositionIdentity, restored.Lifecycle.Snapshot.CompositionIdentity);
    }
}
