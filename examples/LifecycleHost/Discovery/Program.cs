using System.Net;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Modules;
using Hoard.Application.Discovery;
using Hoard.Fixtures.Configuration.LegacyOptions;
using Hoard.Fixtures.Lifecycle.Artifact.One;
using Hoard.Fixtures.Lifecycle.Identity;
using Hoard.Fixtures.Lifecycle.Protocol.One;
using Hoard.Fixtures.Lifecycle.Protocol.Two;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using LifecycleHost.Adapters;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
#if CUSTOM
using Hoard.Fixtures.Lifecycle.Artifact.Two;
#endif

using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
var journeys = new List<object>();
var observations = new List<JsonNode>();
var responseBodies = new List<string>();
await Journey("baseline", "fixture.protocol.one", "fixture.artifact.one");
await Journey("bundled-restart", "fixture.protocol.two", "fixture.artifact.one");
var invalidWeb = Web();
var invalidBuilder = Registry(invalidWeb.Services);
var beforeInvalid = ProtocolOneModule.Events.Count + ProtocolTwoModule.Events.Count;
await using (var invalid = await invalidBuilder.EvaluateConfigurationAsync(new(Document("absent", "fixture.artifact.one")),
    new("0.1.0", "0.1.0"), new(), cancellationToken: timeout.Token))
{
    Require(invalid.Outcome == HoardConfigurationOutcome.Failed && invalid.Configuration is null, "invalid-replacement");
    var activityDelta = ProtocolOneModule.Events.Count + ProtocolTwoModule.Events.Count - beforeInvalid;
    Require(activityDelta == 0, "invalid-no-activation");
    journeys.Add(new { id = "invalid-replacement", passed = true, diagnostics = invalid.Report.Diagnostics.Length, activityDelta });
}
await Journey("recovery", "fixture.protocol.one", "fixture.artifact.one");
#if CUSTOM
await Journey("custom-rebuild", "fixture.protocol.one", "fixture.artifact.two");
#endif
Require(observations.Select(value => value!["observation"]!["lifecycleId"]!.GetValue<string>()).Distinct().Count() == observations.Count, "new-lifecycle");
Console.WriteLine(JsonSerializer.Serialize(new { journeys, observations, responseBodies }));

async Task Journey(string name, string protocol, string artifact)
{
    ProtocolOneModule.Events.Clear();
    ProtocolTwoModule.Events.Clear();
    InspectionService.Constructors = InspectionService.Calls = 0;
    var web = Web();
    var builder = Registry(web.Services);
    var file = name == "baseline" ? "baseline.json" : name == "custom-rebuild" ? "custom.json" : null;
    var environment = new Dictionary<string, string> { ["INVENTED_DISCOVERY_CREDENTIAL"] = "invented-configuration-credential" };
    await using var evaluated = await builder.EvaluateConfigurationAsync(
        new(Document(protocol, artifact), explicitFile: file is null ? null : Path.Combine(AppContext.BaseDirectory, file), environment: environment),
        new("0.1.0", "0.1.0"), new(), cancellationToken: timeout.Token);
    Require(evaluated.Outcome == HoardConfigurationOutcome.Validated, "evaluation");
    await using var lease = await builder.ComposeHoardModulesAsync(evaluated.Configuration!, timeout.Token);
    var app = await web.BuildHoardApplicationAsync(lease, timeout.Token);
    app.MapHoardDiscovery(lease);
    await app.MapHoardModulesAsync(lease, timeout.Token);
    await app.StartAsync(timeout.Token);
    using var client = app.GetTestClient();
    using var response = await client.GetAsync("/api/v1/discovery", timeout.Token);
    Require(response.StatusCode == HttpStatusCode.OK, "read");
    var body = await response.Content.ReadAsByteArrayAsync(timeout.Token);
    var observation = JsonNode.Parse(body)!;
    var modules = observation["modules"]!.AsArray();
    var selected = modules.Single(module => module!["id"]!.GetValue<string>() == protocol)!;
    Require(selected["enabled"]!.GetValue<bool>() && selected["capabilities"]![0]!["availability"]!.GetValue<string>() == "usable", "truthful-operation");
    Require(!modules.Single(module => module!["id"]!.GetValue<string>() == "fixture.unregistered")!["registered"]!.GetValue<bool>(), "included-unregistered");
    Require(modules.Any(module => !module!["enabled"]!.GetValue<bool>() && module["registered"]!.GetValue<bool>()), "registered-disabled");
    Require(!modules.Any(module => module!["id"]!.GetValue<string>() == "unknown-module"), "no-invented-module");
    Require(InspectionService.Constructors == 0 && InspectionService.Calls == 0, "read-does-not-resolve");
    var one = protocol == "fixture.protocol.one";
    var calls = (one ? ProtocolOneModule.Events : ProtocolTwoModule.Events).Count(value => value == "request");
    Require(await client.GetStringAsync(one ? "/fixture/one" : "/fixture/two", timeout.Token) == (one ? "lifecycle-one" : "lifecycle-two"), "actual-route");
    Require((one ? ProtocolOneModule.Events : ProtocolTwoModule.Events).Count(value => value == "request") == calls + 1, "route-counter");
    app.Services.GetRequiredService<InspectionService>().Inspect();
    Require(InspectionService.Constructors == 1 && InspectionService.Calls == 1, "actual-service");
    Require((one ? ProtocolTwoModule.Events : ProtocolOneModule.Events).IsEmpty, "disabled-events");
    Require(LegacyOptionsModule.Accepted > 0, "retained-provider");
    if (file is not null)
    {
        var path = Path.Combine(AppContext.BaseDirectory, file);
        var original = await File.ReadAllTextAsync(path, timeout.Token);
        try
        {
            await File.WriteAllTextAsync(path, Document("absent", artifact), timeout.Token);
            Require(lease.BindHoardDiscovery(app).Capture().Observation!.Modules.Single(module => module.Id == protocol).Enabled, "fixed-selection");
        }
        finally { await File.WriteAllTextAsync(path, original, timeout.Token); }
    }
    await app.StopHoardApplicationAsync(lease, timeout.Token);
    Require(lease.BindHoardDiscovery(app).Capture().Observation!.Phase == "stopped", "terminal-observation");
    observations.Add(observation);
    responseBodies.Add(Convert.ToBase64String(body));
    journeys.Add(new
    {
        id = name,
        passed = true,
        lifecycleId = observation["observation"]!["lifecycleId"]!.GetValue<string>(),
        routeCalls = 1,
        serviceCalls = InspectionService.Calls,
        bytes = body.Length
    });
}

static WebApplicationBuilder Web()
{
    var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
    web.Logging.ClearProviders();
    web.WebHost.UseTestServer();
    web.Services.AddAuthorization(options => options.AddPolicy("Hoard.Management.Read", policy => policy.RequireAssertion(_ => true)));
    web.Services.AddSingleton<IDiscoveryExposureAdapter, FixtureExposure>();
    return web;
}

static HoardBuilder Registry(IServiceCollection services)
{
    var contract = new HoardModuleConfiguration(1, [new("label", HoardOptionType.String, true), new("credential", HoardOptionType.Secret)]);
    static ModuleDescriptor Protocol(ModuleDescriptor declaration) => declaration with
    { Capabilities = [new() { Id = "inspect", Version = "0.1.0", Description = "Synthetic fixture operation" }] };
    var builder = services.AddHoard()
        .AddModule<ProtocolOneProvider>(Protocol(ProtocolOneProvider.Declaration)).AddModuleLifecycle<ProtocolOneProvider, One>()
        .AddModuleConfiguration<ProtocolOneProvider>(contract)
        .AddModule<ProtocolTwoProvider>(Protocol(ProtocolTwoProvider.Declaration)).AddModuleLifecycle<ProtocolTwoProvider, Two>()
        .AddModuleConfiguration<ProtocolTwoProvider>(contract)
        .AddModule<LegacyOptionsProvider>(LegacyOptionsProvider.Declaration).AddModuleLifecycle<LegacyOptionsProvider, LegacyOptionsModule>()
        .AddModuleConfiguration<LegacyOptionsProvider>(new(1, [new("label", HoardOptionType.String, true), new("credential", HoardOptionType.Secret, true)]))
        .AddModule<ArtifactOneProvider>(ArtifactOneProvider.Declaration).AddModuleLifecycle<ArtifactOneProvider, ArtifactOneModule>()
        .AddModule<IdentityProvider>(IdentityProvider.Declaration).AddModuleLifecycle<IdentityProvider, IdentityModule>();
#if CUSTOM
    builder.AddModule<ArtifactTwoProvider>(ArtifactTwoProvider.Declaration).AddModuleLifecycle<ArtifactTwoProvider, ArtifactTwoModule>();
#endif
    var included = IdentityProvider.Declaration with { Id = "fixture.unregistered" };
    return builder.AddHoardDiscovery(new("package-discovery-fixture", "0.1.0", "partial")
    {
        IncludedModules = [included],
        Contributions = [Contribution("fixture.protocol.one"), Contribution("fixture.protocol.two")],
        ServiceBindings = [new("one-service", "fixture.protocol.one", typeof(InspectionService)), new("two-service", "fixture.protocol.two", typeof(InspectionService))]
    }, new() { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });

    static DiscoveryContribution Contribution(string owner) => new("inspect", "0.1.0", "inspect", [owner])
    {
        Support = "supported",
        EvidenceScope = "fixture",
        EvidenceIds = ["package-route-service-fixture"],
        Routes = [new(owner, "lifecycle-test", "GET")],
        Services = [owner.EndsWith("one", StringComparison.Ordinal) ? "one-service" : "two-service"]
    };
}

static string Document(string protocol, string artifact) => new JsonObject
{
    ["configurationversion"] = 1,
    ["enabledmodules"] = new JsonArray("fixture.legacy-options", artifact, protocol),
    ["metadatamodule"] = "fixture.legacy-options",
    ["artifactmodule"] = artifact,
    ["identitymodules"] = new JsonArray(),
    ["requiredcapabilities"] = new JsonArray(),
    ["modules"] = new JsonObject
    {
        [protocol] = JsonNode.Parse("""{"optionsversion":1,"options":{"label":"configured"}}"""),
        ["fixture.legacy-options"] = JsonNode.Parse("""
            {"optionsversion":1,"options":{"label":"configured-old-provider","credential":{"kind":"env","target":"INVENTED_DISCOVERY_CREDENTIAL"}}}
            """)
    }
}.ToJsonString();
static void Require(bool condition, string step)
{ if (!condition) { throw new InvalidOperationException($"Discovery fixture assertion failed: {step}."); } }

sealed class FixtureExposure : IDiscoveryExposureAdapter
{
    public bool Verified => true;
    public bool Allows(HttpContext context) => true;
}
sealed class InspectionService
{
    internal static int Constructors;
    internal static int Calls;
    public InspectionService() => Interlocked.Increment(ref Constructors);
    internal void Inspect() => Interlocked.Increment(ref Calls);
}
abstract class ProtocolAdapter<T>(T inner) : IHoardModule, IHoardConfiguredModule where T : IHoardModule, IHoardConfiguredModule
{
    public void ConfigureOptions(HoardModuleOptions options) => inner.ConfigureOptions(options);
    public void ConfigureServices(IServiceCollection services) { inner.ConfigureServices(services); services.AddSingleton<InspectionService>(); }
    public void MapEndpoints(HoardModuleEndpointBuilder routes) => inner.MapEndpoints(routes);
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token) => inner.InitializeAsync(services, token);
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) => inner.CheckReadinessAsync(token);
    public Task RunAsync(CancellationToken token) => inner.RunAsync(token);
    public ValueTask StopAsync(CancellationToken token) => inner.StopAsync(token);
}
sealed class One() : ProtocolAdapter<ProtocolOneModule>(new());
sealed class Two() : ProtocolAdapter<ProtocolTwoModule>(new());
