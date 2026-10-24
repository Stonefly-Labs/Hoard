using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Hoard.Fixtures.Conformance.Host;

public static class CompositionFixtures
{
    public static readonly HoardPlatformVersions Versions = new("0.1.0", "0.1.0");
    public static ModuleDescriptor Declaration(string id, ModuleCategory category) => new()
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
        Health = [],
        Endpoints = [new() { Id = "probe", Description = "In-process observation." }],
        Provenance = new() { Publisher = "Hoard conformance fixtures", SupportStatus = ModuleSupportStatus.Fixture }
    };

    public static ModuleDependency Dependency(string id, bool optional = false,
        string range = "[0.1.0,0.2.0)", bool prerelease = false) => new()
        { ModuleId = id, VersionRange = range, Optional = optional, AllowPrerelease = prerelease };

    public static HoardStartupSelection Selection(params string[] extra) => new()
    {
        EnabledModuleIds = ["metadata", "artifact", .. extra],
        MetadataModuleId = "metadata",
        ArtifactModuleId = "artifact",
        RequiredCapabilities = []
    };

    public sealed class Probe
    {
        public int Constructors;
        public int Services;
        public int Maps;
        public int Requests;
        public int Connections;
        public int Initializations;
        public int Assessments;
        public int Workers;
        public int Stops;
        public int Disposals;
        public string Path { get; set; } = "/probe";
        public Func<CancellationToken, Task>? Initialize { get; set; }
        public Func<CancellationToken, Task<HoardModuleReadiness>>? Assess { get; set; }
        public Func<CancellationToken, Task>? Worker { get; set; }
        public Func<CancellationToken, Task>? Stop { get; set; }
        public Func<Task>? Request { get; set; }
        public Action<HoardModuleEndpointBuilder>? Map { get; set; }
        public TaskCompletionSource Settled { get; } = Barrier();
        public HoardModuleOptions? Options { get; set; }
        public Task? InitializationWork { get; set; }
        public Task? ShutdownWork { get; set; }
    }

    public static TaskCompletionSource Barrier() => new(TaskCreationOptions.RunContinuationsAsynchronously);

    // Each closed adapter type has its own explicit probe; no assembly scanning or DI discovery.
    public sealed class Module<T> : IHoardModule, IHoardConfiguredModule, IAsyncDisposable where T : class
    {
        public static Probe Observation { get; set; } = new();
        private readonly Probe probe;
        public Module() { probe = Observation; Interlocked.Increment(ref probe.Constructors); }
        public void ConfigureOptions(HoardModuleOptions options) => probe.Options = options;
        public void ConfigureServices(IServiceCollection services)
        {
            Interlocked.Increment(ref probe.Services);
            services.AddSingleton(_ => this);
        }
        public void MapEndpoints(HoardModuleEndpointBuilder endpoints)
        {
            Interlocked.Increment(ref probe.Maps);
            if (probe.Map is { } map) { map(endpoints); return; }
            endpoints.Map("probe", probe.Path, ["GET"], async context =>
            {
                Interlocked.Increment(ref probe.Requests);
                if (probe.Request is { } request) { await request(); }
                await context.Response.WriteAsync("conformance");
            });
        }
        public async ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
        {
            _ = services.GetRequiredService<Module<T>>();
            Interlocked.Increment(ref probe.Initializations);
            Interlocked.Increment(ref probe.Connections);
            try
            {
                if (probe.Initialize is { } initialize)
                {
                    probe.InitializationWork = initialize(token);
                    await probe.InitializationWork;
                }
            }
            finally { probe.Settled.TrySetResult(); }
        }
        public async ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token)
        {
            Interlocked.Increment(ref probe.Assessments);
            return probe.Assess is { } assess ? await assess(token) : new(true, []);
        }
        public Task RunAsync(CancellationToken token)
        {
            Interlocked.Increment(ref probe.Workers);
            return probe.Worker?.Invoke(token) ?? Task.CompletedTask;
        }
        public async ValueTask StopAsync(CancellationToken token)
        {
            Interlocked.Increment(ref probe.Stops);
            if (probe.Stop is { } stop)
            {
                probe.ShutdownWork = stop(token);
                await probe.ShutdownWork;
            }
        }
        public ValueTask DisposeAsync() { Interlocked.Increment(ref probe.Disposals); return ValueTask.CompletedTask; }
    }

    public sealed class Metadata : IMetadataProvider;
    public sealed class MetadataOther : IMetadataProvider;
    public sealed class Artifact : IArtifactProvider;
    public sealed class ArtifactOther : IArtifactProvider;
    public sealed class Protocol : IProtocolProvider;
    public sealed class ProtocolOther : IProtocolProvider;
    public sealed class Identity : IIdentityProvider;
    public sealed class IdentityOther : IIdentityProvider;

    public static Probe Add<T>(HoardBuilder builder, ModuleDescriptor declaration) where T : class, IHoardProvider
    {
        var probe = new Probe { Path = "/" + declaration.Id };
        Module<T>.Observation = probe;
        builder.AddModule<T>(declaration).AddModuleLifecycle<T, Module<T>>();
        return probe;
    }

    public sealed class Registry
    {
        public WebApplicationBuilder Web { get; } = CreateWeb();
        public HoardBuilder Builder { get; }
        public Dictionary<string, Probe> Probes { get; } = [];
        public Registry()
        {
            Builder = Web.Services.AddHoard();
            Probes["metadata"] = Add<Metadata>(Builder, Declaration("metadata", ModuleCategory.Metadata));
            Probes["artifact"] = Add<Artifact>(Builder, Declaration("artifact", ModuleCategory.Artifact));
        }
        public Probe Protocol(ModuleDescriptor? declaration = null)
        {
            var value = declaration ?? Declaration("protocol", ModuleCategory.Protocol);
            return Probes[value.Id] = Add<Protocol>(Builder, value);
        }
        public void Replace(string id, Func<ModuleDescriptor, ModuleDescriptor> change)
        {
            var descriptor = Builder.Services.Single(item =>
                item.ImplementationInstance is HoardModuleRegistration registration && registration.Declaration.Id == id);
            var registration = (HoardModuleRegistration)descriptor.ImplementationInstance!;
            Builder.Services.Remove(descriptor);
            Builder.Services.AddSingleton(registration with { Declaration = change(registration.Declaration) });
        }
        public HoardCompositionValidation Validate(HoardStartupSelection? selection = null,
            HoardLifecycleOptions? options = null, TimeProvider? clock = null) =>
            Builder.ValidateComposition(selection ?? Selection(), Versions, options ?? new(), clock);
        public async Task<Running> BuildAsync(HoardValidatedComposition composition)
        {
            var lease = await Builder.ComposeHoardModulesAsync(composition);
            var app = await Web.BuildHoardApplicationAsync(lease);
            return new(app, lease);
        }
    }

    public static WebApplicationBuilder CreateWeb()
    {
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseTestServer();
        return web;
    }

    public sealed record Running(WebApplication App, HoardServiceComposition Lease) : IAsyncDisposable
    {
        public async Task StartAsync()
        {
            await App.MapHoardModulesAsync(Lease);
            await App.StartAsync();
        }
        public ValueTask DisposeAsync() => Lease.DisposeAsync();
    }
}

#if CONFORMANCE_PROVIDER_PACKAGES
public sealed class PackagedComposition : IAsyncDisposable
{
    private readonly bool ownsRoot;
    public string Root { get; }
    public string ArtifactRoot => Path.Combine(Root, "artifacts");
    public string DatabasePath => Path.Combine(Root, "metadata.db");
    public string DisabledRoot => Path.Combine(Root, "disabled");
    public WebApplicationBuilder Web { get; } = CompositionFixtures.CreateWeb();
    public HoardBuilder Builder { get; }
    public Dictionary<string, CompositionFixtures.Probe> Probes { get; } = [];

    public PackagedComposition(string? root = null)
    {
        ownsRoot = root is null;
        Root = root ?? Path.GetFullPath(Path.Combine("ConformanceRuns", Guid.NewGuid().ToString("N")));
        if (OperatingSystem.IsWindows()) { Directory.CreateDirectory(Root); }
        else { Directory.CreateDirectory(Root, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
        Builder = Hoard.Fixtures.Metadata.Hosting.MetadataFixtureRegistration.AddMetadataFixture(Web.Services.AddHoard());
        Hoard.Fixtures.Artifacts.HostAdapters.ArtifactFixtureRegistration.AddArtifactFixture(Builder);
        Hoard.Fixtures.Artifacts.HostAdapters.ArtifactFixtureRegistration.AddArtifactFixture<CompositionFixtures.ArtifactOther>(
            Builder, "fixture.disabled");
        Probes["protocol"] = CompositionFixtures.Add<CompositionFixtures.Protocol>(Builder,
            CompositionFixtures.Declaration("protocol", ModuleCategory.Protocol));
        Probes["identity"] = CompositionFixtures.Add<CompositionFixtures.Identity>(Builder,
            CompositionFixtures.Declaration("identity", ModuleCategory.Identity));
    }

    public string Configuration(string metadata, string artifact, bool createEmpty = true) =>
        System.Text.Json.JsonSerializer.Serialize(new
        {
            configurationVersion = 1,
            enabledModules = new[] { "fixture.metadata", "fixture.artifact", "protocol", "identity" },
            metadataModule = "fixture.metadata",
            artifactModule = "fixture.artifact",
            identityModules = new[] { "identity" },
            requiredCapabilities = Array.Empty<object>(),
            modules = new Dictionary<string, object>
            {
                ["fixture.metadata"] = new { optionsVersion = 1, options = new { provider = metadata, createEmpty, databasePath = DatabasePath } },
                ["fixture.artifact"] = new { optionsVersion = 1, options = new { provider = artifact, root = ArtifactRoot } },
                ["fixture.disabled"] = new { optionsVersion = 999, options = new { provider = "invalid", root = DisabledRoot } },
                ["protocol"] = new { optionsVersion = 1, options = new { } },
                ["identity"] = new { optionsVersion = 1, options = new { } }
            }
        });

    public ValueTask DisposeAsync()
    {
        if (ownsRoot) { Directory.Delete(Root, true); }
        return ValueTask.CompletedTask;
    }
}
#endif
