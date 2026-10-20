using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleReadinessTests
{
    [Fact]
    public void Optional_unhealthy_observation_does_not_override_explicit_module_status()
    {
        var declaration = LifecycleFixtures.Declaration("metadata", Hoard.Abstractions.Modules.ModuleCategory.Metadata) with
        { Health = [new() { Id = "optional", Description = "Fixture", RequiredForReadiness = false }] };
        Assert.True(HoardReadinessEvaluator.Valid(declaration, new(true, [new("optional", HoardHealthReason.Unavailable)])));
        Assert.True(HoardReadinessEvaluator.Valid(declaration, new(false, [new("optional", HoardHealthReason.Ready)])));
        Assert.False(HoardReadinessEvaluator.Valid(declaration with
        { Health = [new() { Id = "optional", Description = "Fixture", RequiredForReadiness = true }] },
            new(true, [new("optional", HoardHealthReason.Unavailable)])));
    }

    [Fact]
    public async Task Concurrent_readiness_assessments_share_work_and_cancel_only_individual_waits()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Readiness = async _ => { entered.SetResult(); await release.Task; return new(true, []); };
        var first = lease.Lifecycle.AssessReadinessAsync();
        using var cancellation = new CancellationTokenSource();
        var second = lease.Lifecycle.AssessReadinessAsync(cancellation.Token);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            cancellation.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => second);
            Assert.False(first.IsCompleted);
            release.SetResult();
            Assert.True((await first).Ready);
            Assert.Equal(2, LifecycleFixtures.For("artifact").Calls.Count(item => item == "readiness"));
        }
        finally { release.TrySetResult(); await first.WaitAsync(TimeSpan.FromSeconds(5)); }
        await app.StopHoardApplicationAsync(lease);
    }

    [Fact]
    public async Task Later_readiness_loss_and_recovery_do_not_change_selection_or_admission()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        LifecycleFixtures.For("metadata").Readiness = _ => Task.FromResult(new HoardModuleReadiness(false, []));
        var unhealthy = await lease.Lifecycle.AssessReadinessAsync();
        Assert.False(unhealthy.Ready);
        Assert.True(unhealthy.StartupAdmission);
        LifecycleFixtures.For("metadata").Readiness = _ => Task.FromResult(new HoardModuleReadiness(true, []));
        var recovered = await lease.Lifecycle.AssessReadinessAsync();
        Assert.True(recovered.Ready);
        Assert.Equal(unhealthy.CompositionIdentity, recovered.CompositionIdentity);
        await app.StopHoardApplicationAsync(lease);
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("duplicate")]
    [InlineData("unknown")]
    [InlineData("invalid")]
    public void Required_health_observations_are_not_inferred(string kind)
    {
        var declaration = LifecycleFixtures.Declaration("metadata", Hoard.Abstractions.Modules.ModuleCategory.Metadata) with
        { Health = [new() { Id = "probe", Description = "Fixture", RequiredForReadiness = true }] };
        var result = kind switch
        {
            "missing" => new HoardModuleReadiness(true, []),
            "duplicate" => new(true, [new("probe", HoardHealthReason.Ready), new("probe", HoardHealthReason.Ready)]),
            "unknown" => new(true, [new("unknown", HoardHealthReason.Ready)]),
            _ => new(true, [new("probe", (HoardHealthReason)99)])
        };
        Assert.False(HoardReadinessEvaluator.Valid(declaration, result));
        Assert.True(HoardReadinessEvaluator.Valid(declaration, new(true, [new("probe", HoardHealthReason.Ready)])));
    }
}
