using System.Net;
using System.Text.Json;
using Hoard.Fixtures.Lifecycle.Artifact.One;
using Hoard.Fixtures.Lifecycle.Identity;
using Hoard.Fixtures.Lifecycle.Metadata;
using Hoard.Fixtures.Lifecycle.Protocol.One;
using Hoard.Fixtures.Lifecycle.Protocol.Two;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using LifecycleHost.Adapters;
using Microsoft.AspNetCore.TestHost;
#if CUSTOM
using Hoard.Fixtures.Lifecycle.Artifact.Two;
#endif

using var bound = new CancellationTokenSource(TimeSpan.FromSeconds(20));
var journeys = new List<object>();
await Journey("bundled-one", "fixture.protocol.one", "fixture.artifact.one");
await Journey("bundled-two-same-binary", "fixture.protocol.two", "fixture.artifact.one");
#if CUSTOM
await Journey("custom-artifact", "fixture.protocol.one", "fixture.artifact.two");
#endif
var invalid = new ServiceCollection().AddHoard().ValidateComposition(new()
{
    EnabledModuleIds = ["absent"],
    MetadataModuleId = "fixture.metadata",
    ArtifactModuleId = "fixture.artifact.one",
    RequiredCapabilities = []
}, new("0.1.0", "0.1.0"), new());
Require(invalid.Composition is null && invalid.Diagnostics.Length > 0, "invalid-replacement");
await Journey("explicit-recovery", "fixture.protocol.one", "fixture.artifact.one");
Console.WriteLine(JsonSerializer.Serialize(new { journeys }));

async Task Journey(string name, string protocol, string artifact)
{
    ProtocolOneModule.Events.Clear();
    ProtocolTwoModule.Events.Clear();
    IdentityModule.Events.Clear();
    var connectionsOne = ProtocolOneModule.ConnectionAttempts;
    var connectionsTwo = ProtocolTwoModule.ConnectionAttempts;
    var artifactOneConnections = ArtifactOneProvider.ConnectionAttempts;
#if CUSTOM
    var artifactTwoConnections = ArtifactTwoProvider.ConnectionAttempts;
#endif
    var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
    web.Logging.ClearProviders();
    web.WebHost.UseTestServer();
    var builder = web.Services.AddHoard()
        .AddModule<ProtocolOneProvider>(ProtocolOneProvider.Declaration)
        .AddModuleLifecycle<ProtocolOneProvider, ProtocolOneModule>()
        .AddModule<ProtocolTwoProvider>(ProtocolTwoProvider.Declaration)
        .AddModuleLifecycle<ProtocolTwoProvider, ProtocolTwoModule>()
        .AddModule<MetadataProvider>(MetadataProvider.Declaration)
        .AddModuleLifecycle<MetadataProvider, MetadataModule>()
        .AddModule<ArtifactOneProvider>(ArtifactOneProvider.Declaration)
        .AddModuleLifecycle<ArtifactOneProvider, ArtifactOneModule>()
        .AddModule<IdentityProvider>(IdentityProvider.Declaration)
        .AddModuleLifecycle<IdentityProvider, IdentityModule>();
#if CUSTOM
    builder.AddModule<ArtifactTwoProvider>(ArtifactTwoProvider.Declaration)
        .AddModuleLifecycle<ArtifactTwoProvider, ArtifactTwoModule>();
#endif
    var selection = new HoardStartupSelection
    {
        EnabledModuleIds = ["fixture.metadata", artifact, protocol],
        MetadataModuleId = "fixture.metadata",
        ArtifactModuleId = artifact,
        RequiredCapabilities = []
    };
    var validation = builder.ValidateComposition(selection, new("0.1.0", "0.1.0"), new());
    Require(validation.Composition is not null && validation.Diagnostics.IsEmpty, "validation");
    await using var lease = await builder.ComposeHoardModulesAsync(validation.Composition!, bound.Token);
    var app = await web.BuildHoardApplicationAsync(lease, bound.Token);
    await app.MapHoardModulesAsync(lease, bound.Token);
    await app.StartAsync(bound.Token);
    var expected = protocol.EndsWith("one", StringComparison.Ordinal) ? "one" : "two";
    var disabled = expected == "one" ? "two" : "one";
    using var client = app.GetTestClient();
    Require(await client.GetStringAsync($"/fixture/{expected}", bound.Token) == $"lifecycle-{expected}", "enabled-route");
    using var absent = await client.GetAsync($"/fixture/{disabled}", bound.Token);
    Require(absent.StatusCode == HttpStatusCode.NotFound, "disabled-route");
    Require((expected == "one" ? ProtocolTwoModule.Events : ProtocolOneModule.Events).IsEmpty, "disabled-activity");
    Require(expected == "one" ? ProtocolTwoModule.ConnectionAttempts == connectionsTwo
        : ProtocolOneModule.ConnectionAttempts == connectionsOne, "disabled-connection-attempts");
#if CUSTOM
    Require(artifact == "fixture.artifact.one" ? ArtifactTwoProvider.ConnectionAttempts == artifactTwoConnections
        : ArtifactOneProvider.ConnectionAttempts == artifactOneConnections, "disabled-artifact-connections");
#else
    Require(ArtifactOneProvider.ConnectionAttempts == artifactOneConnections + 1, "selected-artifact-connection");
#endif
    Require(IdentityModule.Events.IsEmpty, "disabled-identity");
    Require(IdentityModule.ConnectionAttempts == 0, "disabled-identity-connections");
    selection = selection with { EnabledModuleIds = ["absent"] };
    Require(lease.Lifecycle.Snapshot.Modules.Any(module => module.ModuleId == protocol && module.Enabled), "fixed-selection");
#if !CUSTOM
    Require(!lease.Lifecycle.Snapshot.Modules.Any(module => module.ModuleId == "fixture.artifact.two"), "baseline-absence");
#endif
    await app.StopHoardApplicationAsync(lease, bound.Token);
    await lease.DisposeAsync();
    Require(lease.StopResult!.Complete, "release");
    Require(MetadataProvider.Acquisitions == MetadataProvider.Releases
        && ArtifactOneProvider.Acquisitions == ArtifactOneProvider.Releases, "owned-release");
    Require(ProtocolOneModule.ResourceAcquisitions == ProtocolOneModule.ResourceReleases
        && ProtocolTwoModule.ResourceAcquisitions == ProtocolTwoModule.ResourceReleases, "protocol-resource-release");
#if CUSTOM
    Require(ArtifactTwoProvider.Acquisitions == ArtifactTwoProvider.Releases, "custom-resource-release");
#endif
    var events = ProtocolOneModule.Events.Count + ProtocolTwoModule.Events.Count;
    Require(events >= 8, "nonempty-events");
    journeys.Add(new { name, passed = true, events });
}

static void Require(bool condition, string step)
{
    if (!condition) { throw new InvalidOperationException($"Lifecycle fixture assertion failed: {step}."); }
}
