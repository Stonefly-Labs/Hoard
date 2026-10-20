using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class LifecycleContractTests
{
    [Fact]
    public void Adapter_registration_is_type_only_and_does_not_change_legacy_constraints()
    {
        var builder = new ServiceCollection().AddHoard();
        builder.AddModuleLifecycle<LegacyProvider, NeverConstruct>();
        var registration = Assert.Single(builder.Services).ImplementationInstance;
        Assert.Equal(new HoardModuleLifecycleRegistration(typeof(LegacyProvider), typeof(NeverConstruct)), registration);
        Assert.Empty(typeof(HoardValidatedComposition).GetConstructors());
    }

    [Fact]
    public void Options_reject_infinite_zero_negative_but_do_not_expand_small_outer_budget()
    {
        foreach (var duration in new[] { TimeSpan.Zero, Timeout.InfiniteTimeSpan, TimeSpan.FromSeconds(-2) })
        {
            Assert.False(new HoardLifecycleOptions { StartupTimeout = duration }.IsValid);
        }
        Assert.True(new HoardLifecycleOptions { StartupTimeout = TimeSpan.FromMilliseconds(1) }.IsValid);
        Assert.True(new HoardLifecycleOptions { StartupTimeout = TimeSpan.MaxValue }.IsValid);
    }

    private sealed class LegacyProvider(string requiredConstructorArgument) : IProtocolProvider
    {
        public string Value { get; } = requiredConstructorArgument;
    }

    public sealed class NeverConstruct : IHoardModule
    {
        public NeverConstruct() => throw new InvalidOperationException("Must not construct while registering.");
        public void ConfigureServices(IServiceCollection services) => throw new NotSupportedException();
        public void MapEndpoints(Hoard.Hosting.Routing.HoardModuleEndpointBuilder endpoints) => throw new NotSupportedException();
        public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token) => throw new NotSupportedException();
        public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) => throw new NotSupportedException();
        public Task RunAsync(CancellationToken token) => throw new NotSupportedException();
        public ValueTask StopAsync(CancellationToken token) => throw new NotSupportedException();
    }
}
