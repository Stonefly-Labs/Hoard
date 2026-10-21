using System.Collections.Concurrent;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Fixtures.Lifecycle.Protocol.Two;

public sealed class ProtocolTwoProvider : IProtocolProvider
{
    public static ModuleDescriptor Declaration => new()
    {
        Id = "fixture.protocol.two",
        Category = ModuleCategory.Protocol,
        Version = "0.1.0",
        Compatibility = new() { HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
        Dependencies = [],
        Capabilities = [],
        Configuration =
        [
            new() { Key = "label", Description = "Fixture label.", Required = true, SecretReference = false },
            new() { Key = "credential", Description = "Optional fixture reference.", Required = false, SecretReference = true }
        ],
        Health = [],
        Endpoints = [new() { Id = "lifecycle-test", Description = "Fixture-only handler; no package protocol." }],
        Provenance = new() { Publisher = "Hoard lifecycle acceptance", SupportStatus = ModuleSupportStatus.Fixture }
    };
}

public sealed class ProtocolTwoModule : IHoardModule, IHoardConfiguredModule
{
    public static HoardModuleOptions? LastOptions { get; private set; }
    public void ConfigureOptions(HoardModuleOptions options) { LastOptions = options; Events.Enqueue("options"); }
    private bool acquired;
    public static int ConnectionAttempts;
    public static int ResourceAcquisitions;
    public static int ResourceReleases;
    public static ConcurrentQueue<string> Events { get; } = new();
    public static Func<CancellationToken, Task>? Initialize { get; set; }
    public static Func<CancellationToken, Task>? Worker { get; set; }
    public static Func<CancellationToken, Task>? Cleanup { get; set; }
    public static bool Ready { get; set; } = true;
    public ProtocolTwoModule() => Events.Enqueue("construct");
    public void ConfigureServices(IServiceCollection services) => Events.Enqueue("services");
    public void MapEndpoints(HoardModuleEndpointBuilder routes)
    {
        Events.Enqueue("map");
        routes.Map("lifecycle-test", "/fixture/two", ["GET"], context =>
        { Events.Enqueue("request"); return context.Response.WriteAsync("lifecycle-two"); });
    }
    public async ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
    {
        Events.Enqueue("initialize");
        Interlocked.Increment(ref ConnectionAttempts);
        Interlocked.Increment(ref ResourceAcquisitions);
        acquired = true;
        if (Initialize is { } callback) { await callback(token); }
    }
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token)
    { Events.Enqueue("readiness"); return ValueTask.FromResult(new HoardModuleReadiness(Ready, [])); }
    public Task RunAsync(CancellationToken token) { Events.Enqueue("worker"); return Worker?.Invoke(token) ?? Task.CompletedTask; }
    public async ValueTask StopAsync(CancellationToken token)
    {
        Events.Enqueue("stop");
        if (Cleanup is { } callback) { await callback(token); }
        if (acquired) { Interlocked.Increment(ref ResourceReleases); acquired = false; }
    }
}
