using System.Net;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Fixtures.Lifecycle.Artifact.One;
using Hoard.Fixtures.Lifecycle.Identity;
using Hoard.Fixtures.Lifecycle.Metadata;
using Hoard.Fixtures.Lifecycle.Protocol.One;
using Hoard.Fixtures.Lifecycle.Protocol.Two;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Configuration.Conversion;
using Hoard.Hosting.Lifecycle;
using LifecycleHost.Adapters;
using Microsoft.AspNetCore.TestHost;
#if CUSTOM
using Hoard.Fixtures.Lifecycle.Artifact.Two;
#endif
#if CONFIGURATION_LEGACY
using Hoard.Fixtures.Configuration.LegacyOptions;
#endif

internal static class ConfigurationJourneys
{
    internal static async Task RunAsync(CancellationToken token)
    {
        var journeys = new List<object>();
        var environment = new Dictionary<string, string>(StringComparer.Ordinal)
        { ["INVENTED_CONFIGURATION_SECRET"] = "invented-configuration-credential" };
        var previewReads = 0;
        var previewBuilder = Registry(Web().Services);
        var synthetic = Path.Combine(AppContext.BaseDirectory, "synthetic-fixture-v0.json");
        await using (var preview = await previewBuilder.PreviewConfigurationConversionAsync(
            synthetic, synthetic + $".{Guid.NewGuid():N}.new", new("0.1.0", "0.1.0"), new(),
            readEnvironment: (_, _) => { previewReads++; return ValueTask.FromResult<string?>(null); },
            cancellationToken: token))
        {
            Require(preview.Outcome == HoardConfigurationOutcome.Validated && preview.Session is not null, "synthetic-example");
            Require(previewReads == 0, "secret-free-preview");
        }
        await Start("configured-one", "fixture.protocol.one", "fixture.artifact.one");
        await Start("configured-two-same-binary", "fixture.protocol.two", "fixture.artifact.one");
        ProtocolOneModule.Events.Clear();
        ProtocolTwoModule.Events.Clear();
        var invalidWeb = Web();
        var invalid = Registry(invalidWeb.Services);
        await using (var result = await invalid.EvaluateConfigurationAsync(new(Document("absent", "fixture.artifact.one"),
            environment: environment), new("0.1.0", "0.1.0"), new(), cancellationToken: token))
        {
            Require(result.Configuration is null && result.Outcome == HoardConfigurationOutcome.Failed, "invalid-replacement");
            Require(ProtocolOneModule.Events.IsEmpty && ProtocolTwoModule.Events.IsEmpty, "rejected-construction");
            journeys.Add(new { name = "invalid-replacement", passed = true, events = result.Report.Diagnostics.Length });
        }
        await Start("explicit-recovery", "fixture.protocol.one", "fixture.artifact.one");
#if CUSTOM
        await Start("configured-custom-artifact", "fixture.protocol.one", "fixture.artifact.two");
#endif
        Console.WriteLine(JsonSerializer.Serialize(new { journeys }));

        async Task Start(string name, string protocol, string artifact)
        {
            ProtocolOneModule.Events.Clear();
            ProtocolTwoModule.Events.Clear();
            var before = protocol.EndsWith("one", StringComparison.Ordinal)
                ? ProtocolTwoModule.ConnectionAttempts : ProtocolOneModule.ConnectionAttempts;
            var web = Web();
            var builder = Registry(web.Services);
            var file = name switch
            {
                "configured-one" => Path.Combine(AppContext.BaseDirectory, "baseline.json"),
                "configured-custom-artifact" => Path.Combine(AppContext.BaseDirectory, "custom.json"),
                _ => null
            };
            await using var evaluated = await builder.EvaluateConfigurationAsync(
                new(Document(protocol, artifact), explicitFile: file, environment: environment),
                new("0.1.0", "0.1.0"), new(), cancellationToken: token);
            Require(evaluated.Outcome == HoardConfigurationOutcome.Validated, "configured-evaluation");
            await using var lease = await builder.ComposeHoardModulesAsync(evaluated.Configuration!, token);
            var app = await web.BuildHoardApplicationAsync(lease, token);
            await app.MapHoardModulesAsync(lease, token);
            await app.StartAsync(token);
            var one = protocol.EndsWith("one", StringComparison.Ordinal);
            using var client = app.GetTestClient();
            Require(await client.GetStringAsync(one ? "/fixture/one" : "/fixture/two", token) == (one ? "lifecycle-one" : "lifecycle-two"), "route");
            using var absent = await client.GetAsync(one ? "/fixture/two" : "/fixture/one", token);
            Require(absent.StatusCode == HttpStatusCode.NotFound, "disabled-route");
            Require((one ? ProtocolTwoModule.Events : ProtocolOneModule.Events).IsEmpty, "disabled-events");
            Require((one ? ProtocolTwoModule.ConnectionAttempts : ProtocolOneModule.ConnectionAttempts) == before, "disabled-connections");
            var fixedOptions = one ? ProtocolOneModule.LastOptions! : ProtocolTwoModule.LastOptions!;
            Require(fixedOptions.GetString("label") == "configured", "owner-options");
            environment["INVENTED_CONFIGURATION_SECRET"] = "changed-after-evaluation";
            Require(fixedOptions.GetSecret("credential").Reveal() == "invented-configuration-credential", "fixed-secret");
            environment["INVENTED_CONFIGURATION_SECRET"] = "invented-configuration-credential";
#if CONFIGURATION_LEGACY
            Require(LegacyOptionsModule.Accepted > 0, "unchanged-old-provider-adapter");
#endif
            await app.StopHoardApplicationAsync(lease, token);
            await lease.DisposeAsync();
            Require(lease.StopResult!.Complete, "release");
            journeys.Add(new { name, passed = true, events = ProtocolOneModule.Events.Count + ProtocolTwoModule.Events.Count });
        }
    }

    private static WebApplicationBuilder Web()
    {
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseTestServer();
        return web;
    }

    private static HoardBuilder Registry(IServiceCollection services)
    {
        var contract = new HoardModuleConfiguration(1,
            [new("label", HoardOptionType.String, true) { MinimumLength = 1 }, new("credential", HoardOptionType.Secret)]);
        var builder = services.AddHoard()
            .AddModule<ProtocolOneProvider>(ProtocolOneProvider.Declaration).AddModuleLifecycle<ProtocolOneProvider, ProtocolOneModule>()
            .AddModuleConfiguration<ProtocolOneProvider>(contract)
            .AddModule<ProtocolTwoProvider>(ProtocolTwoProvider.Declaration).AddModuleLifecycle<ProtocolTwoProvider, ProtocolTwoModule>()
            .AddModuleConfiguration<ProtocolTwoProvider>(contract)
            .AddModule<ArtifactOneProvider>(ArtifactOneProvider.Declaration).AddModuleLifecycle<ArtifactOneProvider, ArtifactOneModule>()
            .AddModule<IdentityProvider>(IdentityProvider.Declaration).AddModuleLifecycle<IdentityProvider, IdentityModule>();
#if CONFIGURATION_LEGACY
        builder.AddModule<LegacyOptionsProvider>(LegacyOptionsProvider.Declaration).AddModuleLifecycle<LegacyOptionsProvider, LegacyOptionsModule>()
            .AddModuleConfiguration<LegacyOptionsProvider>(new(1, [new("label", HoardOptionType.String, true), new("credential", HoardOptionType.Secret, true)]));
#else
        builder.AddModule<MetadataProvider>(MetadataProvider.Declaration).AddModuleLifecycle<MetadataProvider, MetadataModule>();
#endif
#if CUSTOM
        builder.AddModule<ArtifactTwoProvider>(ArtifactTwoProvider.Declaration).AddModuleLifecycle<ArtifactTwoProvider, ArtifactTwoModule>();
#endif
        return builder;
    }

    private static string Document(string protocol, string artifact)
    {
#if CONFIGURATION_LEGACY
        const string metadata = "fixture.legacy-options";
#else
        const string metadata = "fixture.metadata";
#endif
        var root = new JsonObject
        {
            ["configurationversion"] = 1,
            ["enabledmodules"] = new JsonArray(metadata, artifact, protocol),
            ["metadatamodule"] = metadata,
            ["artifactmodule"] = artifact,
            ["identitymodules"] = new JsonArray(),
            ["requiredcapabilities"] = new JsonArray()
        };
        var options = new JsonObject();
        foreach (var id in new[] { "fixture.protocol.one", "fixture.protocol.two" })
        {
            options[id] = JsonNode.Parse("""
                {"optionsversion":1,"options":{"label":"configured","credential":{"kind":"env","target":"INVENTED_CONFIGURATION_SECRET"}}}
                """);
        }
#if CONFIGURATION_LEGACY
        options[metadata] = JsonNode.Parse("""
            {"optionsversion":1,"options":{"label":"configured-old-provider","credential":{"kind":"env","target":"INVENTED_CONFIGURATION_SECRET"}}}
            """);
#endif
        root["modules"] = options;
        return root.ToJsonString();
    }

    private static void Require(bool condition, string step)
    {
        if (!condition) { throw new InvalidOperationException($"Configuration fixture assertion failed: {step}."); }
    }
}
