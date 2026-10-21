using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryPublicationTests
{
    [Fact]
    public async Task The_authority_publishes_registered_state_before_any_activation_callback()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry().AddHoardDiscovery(new("fixture", "0.1.0", "partial"), new());
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = new HoardServiceComposition(composition);
        var observed = lease.Discovery!.Capture().Observation!;
        Assert.Equal("registered", observed.Phase);
        Assert.Equal(1UL, observed.Revision);
        Assert.Null(observed.ReadinessAssessedAt);
        Assert.False(observed.StartupAdmission);
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Initial_publication_and_terminal_revisions_are_coherent_without_probes()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry()
            .AddHoardDiscovery(new("fixture", "0.1.0", "complete"), new());
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        var lease = await builder.ComposeHoardModulesAsync(composition);
        var source = Assert.IsAssignableFrom<IHoardDiscoverySource>(lease.Discovery);
        var before = Assert.IsType<HoardDiscoveryObservation>(source.Capture().Observation);
        Assert.Null(before.ReadinessAssessedAt);
        Assert.False(before.StartupAdmission);
        var calls = LifecycleFixtures.Controls.Values.Sum(control => control.Calls.Count);
        for (var index = 0; index < 20; index++) { Assert.True(source.Capture().Success); }
        Assert.Equal(calls, LifecycleFixtures.Controls.Values.Sum(control => control.Calls.Count));
        await lease.DisposeAsync();
        var after = Assert.IsType<HoardDiscoveryObservation>(source.Capture().Observation);
        Assert.Equal(before.LifecycleId, after.LifecycleId);
        Assert.True(after.Revision > before.Revision);
        Assert.Equal("stopped", after.Phase);
        Assert.False(after.StartupAdmission);
    }
}
