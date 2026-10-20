using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace Hoard.Composition.Tests;

internal static class LifecycleFixtures
{
    internal static readonly HoardPlatformVersions Versions = new("0.1.0", "0.1.0");
    internal static ModuleDescriptor Declaration(string id, ModuleCategory category) => new()
    {
        Id = id,
        Category = category,
        Version = "0.1.0",
        Compatibility = new()
        {
            HostRange = "[0.1.0,0.2.0)",
            AbstractionsRange = "[0.1.0,0.2.0)",
            AllowPrereleaseHost = false,
            AllowPrereleaseAbstractions = false
        },
        Dependencies = [],
        Capabilities = [],
        Configuration = [],
        Endpoints = [],
        Health = [],
        Provenance = new() { Publisher = "Lifecycle fixtures", SupportStatus = ModuleSupportStatus.Fixture }
    };

    internal static HoardStartupSelection Selection(params string[] extra) => new()
    {
        EnabledModuleIds = ["metadata", "artifact", .. extra],
        MetadataModuleId = "metadata",
        ArtifactModuleId = "artifact",
        RequiredCapabilities = []
    };

    internal static HoardBuilder Registry(IServiceCollection? services = null)
    {
        var builder = (services ?? new ServiceCollection()).AddHoard();
        builder.AddModule<MetadataProvider>(Declaration("metadata", ModuleCategory.Metadata))
            .AddModuleLifecycle<MetadataProvider, MetadataModule>()
            .AddModule<ArtifactProvider>(Declaration("artifact", ModuleCategory.Artifact))
            .AddModuleLifecycle<ArtifactProvider, ArtifactModule>();
        return builder;
    }

    internal sealed class MetadataProvider : IMetadataProvider;
    internal sealed class ArtifactProvider : IArtifactProvider;
    internal sealed class ProtocolProvider : IProtocolProvider;
    internal sealed class IdentityProvider : IIdentityProvider;
    internal sealed class MixedProvider : IProtocolProvider, IArtifactProvider;

    internal sealed class Control
    {
        internal int Constructors;
        internal readonly List<string> Calls = [];
        internal Action<IServiceCollection>? Configure { get; set; }
        internal Action<HoardModuleEndpointBuilder>? Map { get; set; }
        internal Func<CancellationToken, Task>? Initialize { get; set; }
        internal Func<CancellationToken, Task<HoardModuleReadiness>>? Readiness { get; set; }
        internal Func<CancellationToken, Task>? Worker { get; set; }
        internal Func<CancellationToken, Task>? Stop { get; set; }
    }

    internal static readonly Dictionary<string, Control> Controls = [];
    internal static readonly LifecycleTestHarness LogCapture = new();
    internal static void AssertSafe(IEnumerable<HoardLifecycleDiagnostic> diagnostics)
    {
        var errors = diagnostics.ToArray();
        Assert.NotEmpty(errors);
        Assert.All(errors, error =>
        {
            Assert.True(HoardLifecycleDiagnostic.IsSafeId(error.ModuleId));
            Assert.NotEmpty(error.RuleCode);
            Assert.NotEqual(Guid.Empty, error.CorrelationId);
            Assert.InRange(error.CorrectiveAction.Length, 1, 512);
            Assert.InRange(error.DependencyPath.Length, 0, 32);
            Assert.All(error.DependencyPath, id => Assert.True(HoardLifecycleDiagnostic.IsSafeId(id)));
        });
        var output = System.Text.Json.JsonSerializer.Serialize(errors) + string.Join("\n", LogCapture.Logs);
        foreach (var secret in new[] { "seeded-secret", "seeded-late-secret", "constructor-secret", "root-secret" })
        { Assert.DoesNotContain(secret, output); }
    }
    internal static Control For(string id)
    {
        lock (Controls)
        {
            if (!Controls.TryGetValue(id, out var control)) { Controls.Add(id, control = new()); }
            return control;
        }
    }
    internal static void Reset() { lock (Controls) { Controls.Clear(); LogCapture.Logs.Clear(); } }

    public abstract class Module : IHoardModule
    {
        private readonly Control control;
        protected Module(string id) { control = For(id); Interlocked.Increment(ref control.Constructors); Call("construct"); }
        private void Call(string phase) { lock (control.Calls) { control.Calls.Add(phase); } }
        public void ConfigureServices(IServiceCollection services) { Call("services"); control.Configure?.Invoke(services); }
        public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { Call("map"); control.Map?.Invoke(endpoints); }
        public async ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
        { Call("initialize"); if (control.Initialize is { } callback) { await callback(token); } }
        public async ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token)
        {
            Call("readiness");
            return control.Readiness is { } callback ? await callback(token) : new(true, []);
        }
        public Task RunAsync(CancellationToken token) { Call("worker"); return control.Worker?.Invoke(token) ?? Task.CompletedTask; }
        public async ValueTask StopAsync(CancellationToken token)
        { Call("stop"); if (control.Stop is { } callback) { await callback(token); } }
    }
    public sealed class MetadataModule() : Module("metadata");
    public sealed class ArtifactModule() : Module("artifact");
    public sealed class ProtocolModule() : Module("protocol");
    public sealed class IdentityModule() : Module("identity");

    internal static WebApplicationBuilder WebBuilder()
    {
        var builder = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        builder.Logging.ClearProviders();
        builder.Logging.AddProvider(LogCapture);
        builder.WebHost.UseTestServer();
        return builder;
    }
}
