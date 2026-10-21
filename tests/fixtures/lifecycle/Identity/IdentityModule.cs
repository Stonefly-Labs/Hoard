using System.Collections.Concurrent;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Fixtures.Lifecycle.Identity;

public sealed class IdentityProvider : IIdentityProvider
{
    public static ModuleDescriptor Declaration => new()
    {
        Id = "fixture.identity",
        Category = ModuleCategory.Identity,
        Version = "0.1.0",
        Compatibility = new() { HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
        Dependencies = [],
        Capabilities = [],
        Configuration = [],
        Endpoints = [],
        Health = [],
        Provenance = new() { Publisher = "Hoard lifecycle acceptance", SupportStatus = ModuleSupportStatus.Fixture }
    };
}

public sealed class IdentityModule : IHoardModule
{
    public static int ConnectionAttempts;
    public static ConcurrentQueue<string> Events { get; } = new();
    public IdentityModule() => Events.Enqueue("construct");
    public void ConfigureServices(IServiceCollection services) => Events.Enqueue("services");
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) => Events.Enqueue("map");
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
    { Events.Enqueue("initialize"); Interlocked.Increment(ref ConnectionAttempts); return ValueTask.CompletedTask; }
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token)
    { Events.Enqueue("readiness"); return ValueTask.FromResult(new HoardModuleReadiness(true, [])); }
    public Task RunAsync(CancellationToken token) { Events.Enqueue("worker"); return Task.CompletedTask; }
    public ValueTask StopAsync(CancellationToken token) { Events.Enqueue("stop"); return ValueTask.CompletedTask; }
}
