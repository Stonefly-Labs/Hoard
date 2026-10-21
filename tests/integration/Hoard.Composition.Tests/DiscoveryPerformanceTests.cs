using System.Collections.Immutable;
using System.Diagnostics;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.InteropServices;
using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Application.Discovery;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryPerformanceTests
{
    public sealed class PassiveModule : IHoardModule
    {
        internal static int Constructors;
        internal static int Probes;
        internal static int Connections;
        internal static int ActiveResources;
        internal static int ServiceCalls;
        private bool acquired;
        public PassiveModule() => Interlocked.Increment(ref Constructors);
        public void ConfigureServices(IServiceCollection services) { }
        public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
        public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
        {
            Interlocked.Increment(ref Connections);
            Interlocked.Increment(ref ActiveResources);
            acquired = true;
            return ValueTask.CompletedTask;
        }
        public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token)
        { Interlocked.Increment(ref Probes); return ValueTask.FromResult(new HoardModuleReadiness(true, [])); }
        public Task RunAsync(CancellationToken token) => Task.CompletedTask;
        public ValueTask StopAsync(CancellationToken token)
        {
            if (acquired) { Interlocked.Decrement(ref ActiveResources); acquired = false; }
            return ValueTask.CompletedTask;
        }
    }

    [Fact]
    public async Task One_hundred_complete_authorized_reads_of_one_thousand_contributions_have_bounded_local_cost()
    {
        LifecycleFixtures.Reset();
        PassiveModule.Constructors = PassiveModule.Probes = PassiveModule.Connections = PassiveModule.ActiveResources = PassiveModule.ServiceCalls = 0;
        var secrets = 0;
        var web = LifecycleFixtures.WebBuilder();
        DiscoveryFixtures.ConfigureExposure(web.Services);
        var builder = web.Services.AddHoard();
        var assembly = AssemblyBuilder.DefineDynamicAssembly(new("DiscoveryPerformanceFixtures"), AssemblyBuilderAccess.RunAndCollect);
        var module = assembly.DefineDynamicModule("Fixtures");
        var ids = new List<string>();
        for (var index = 0; index < 100; index++)
        {
            var category = index == 0 ? ModuleCategory.Metadata : index == 1 ? ModuleCategory.Artifact : ModuleCategory.Protocol;
            var id = index == 0 ? "metadata" : index == 1 ? "artifact" : $"module-{index}";
            var family = category == ModuleCategory.Metadata ? typeof(IMetadataProvider) :
                category == ModuleCategory.Artifact ? typeof(IArtifactProvider) : typeof(IProtocolProvider);
            var type = module.DefineType($"Fixture{index}", TypeAttributes.Public | TypeAttributes.Sealed);
            type.AddInterfaceImplementation(family);
            type.DefineDefaultConstructor(MethodAttributes.Public);
            var provider = type.CreateType()!;
            var descriptor = LifecycleFixtures.Declaration(id, category) with
            {
                Capabilities = Enumerable.Range(0, 10).Select(number => new CapabilityDeclaration
                { Id = $"capability-{number}", Version = "0.1.0", Description = "Synthetic performance fixture" }).ToImmutableArray()
            };
            builder.Services.AddSingleton(new HoardModuleRegistration { Declaration = descriptor, ProviderType = provider });
            builder.Services.AddSingleton(new HoardModuleLifecycleRegistration(provider, typeof(PassiveModule)));
            ids.Add(id);
        }
        builder.AddHoardDiscovery(new("performance-fixture", "0.1.0", "complete"), new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        web.Services.AddSingleton(_ => { Interlocked.Increment(ref PassiveModule.ServiceCalls); return new DiscoveryFixtures.InspectionService(); });
        var document = new System.Text.Json.Nodes.JsonObject
        {
            ["configurationversion"] = 1,
            ["enabledmodules"] = new System.Text.Json.Nodes.JsonArray(ids.Select(id => (System.Text.Json.Nodes.JsonNode?)System.Text.Json.Nodes.JsonValue.Create(id)).ToArray()),
            ["metadatamodule"] = "metadata",
            ["artifactmodule"] = "artifact",
            ["identitymodules"] = new System.Text.Json.Nodes.JsonArray(),
            ["requiredcapabilities"] = new System.Text.Json.Nodes.JsonArray(),
            ["modules"] = new System.Text.Json.Nodes.JsonObject()
        };
        await using var evaluated = await builder.EvaluateConfigurationAsync(new(document.ToJsonString(),
            readEnvironment: (_, _) => { Interlocked.Increment(ref secrets); return ValueTask.FromResult<string?>(null); }),
            LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluated.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(evaluated.Configuration!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapHoardDiscovery(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var beforeConstructors = PassiveModule.Constructors;
        var beforeProbes = PassiveModule.Probes;
        var beforeConnections = PassiveModule.Connections;
        var beforeResources = PassiveModule.ActiveResources;
        var beforeServices = PassiveModule.ServiceCalls;
        var beforeSecrets = secrets;
        using var client = app.GetTestClient();
        var samples = new double[100];
        var bytes = new int[100];
        var seen = new int[100];
        await Task.WhenAll(Enumerable.Range(0, 10).Select(async worker =>
        {
            for (var sample = worker; sample < 100; sample += 10)
            {
                var started = Stopwatch.GetTimestamp();
                using var response = await client.GetAsync("/api/v1/discovery");
                Assert.True(response.IsSuccessStatusCode);
                var body = await response.Content.ReadAsByteArrayAsync();
                using var parsed = JsonDocument.Parse(body);
                var modules = parsed.RootElement.GetProperty("modules");
                Assert.Equal(100, modules.GetArrayLength());
                Assert.All(modules.EnumerateArray(), entry => Assert.Equal(10, entry.GetProperty("capabilities").GetArrayLength()));
                Assert.Equal("running", parsed.RootElement.GetProperty("host").GetProperty("phase").GetString());
                samples[sample] = Stopwatch.GetElapsedTime(started).TotalSeconds;
                bytes[sample] = body.Length;
                seen[sample] = 1;
            }
        }));
        Assert.All(seen, value => Assert.Equal(1, value));
        Assert.Equal(beforeConstructors, PassiveModule.Constructors);
        Assert.Equal(beforeProbes, PassiveModule.Probes);
        Assert.Equal(beforeConnections, PassiveModule.Connections);
        Assert.Equal(beforeResources, PassiveModule.ActiveResources);
        Assert.Equal(beforeServices, PassiveModule.ServiceCalls);
        Assert.Equal(beforeSecrets, secrets);
        Assert.InRange(samples.Order().ElementAt(94), 0, 2);
        var directory = Environment.GetEnvironmentVariable("HOARD_DISCOVERY_OUTPUT");
        if (directory is not null)
        {
            await File.WriteAllTextAsync(Path.Combine(directory, "performance.json"), JsonSerializer.Serialize(new
            {
                modules = 100,
                contributionsPerModule = 10,
                concurrency = 10,
                completeBodies = 100,
                samples,
                bytes,
                sdk = Environment.GetEnvironmentVariable("HOARD_DISCOVERY_SDK") ?? throw new InvalidOperationException("Missing discovery SDK evidence."),
                runId = Environment.GetEnvironmentVariable("HOARD_DISCOVERY_RUN_ID") ?? throw new InvalidOperationException("Missing discovery run identity."),
                os = RuntimeInformation.OSDescription,
                resourceDeltas = new
                {
                    constructors = PassiveModule.Constructors - beforeConstructors,
                    probes = PassiveModule.Probes - beforeProbes,
                    secrets = secrets - beforeSecrets,
                    serviceCalls = PassiveModule.ServiceCalls - beforeServices,
                    connections = PassiveModule.Connections - beforeConnections,
                    activeResources = PassiveModule.ActiveResources - beforeResources
                }
            }));
        }
    }
}
