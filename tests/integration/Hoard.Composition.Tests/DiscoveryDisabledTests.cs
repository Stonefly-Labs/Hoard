using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryDisabledTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Disabled_operational_failures_do_not_validate_resolve_construct_or_probe(bool incompatible)
    {
        ConfiguredFixtures.Reset();
        var checks = 0;
        var reads = 0;
        var builder = ConfiguredFixtures.Registry();
        var declaration = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Compatibility = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol).Compatibility with
            { HostRange = incompatible ? "[9.0.0,10.0.0)" : "[0.1.0,0.2.0)" },
            Configuration = ConfiguredFixtures.Contract.Fields.Select(field => new ConfigurationRequirement
            {
                Key = field.Key,
                Required = field.Required,
                SecretReference = field.Type == HoardOptionType.Secret,
                Description = DiscoveryTestHarness.Secret
            }).ToImmutableArray()
        };
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(declaration)
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, ConfiguredFixtures.ConfiguredProtocolModule>()
            .AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(ConfiguredFixtures.Contract, (_, _) =>
            { checks++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); })
            .AddHoardDiscovery(new("fixture", "0.1.0", "complete"), new());
        var document = System.Text.Json.Nodes.JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        document["modules"]!["protocol"] = System.Text.Json.Nodes.JsonNode.Parse(
            """{"optionsversion":99,"options":{"label":"","credential":{"kind":"env","target":"INVENTED_DISCOVERY_PRIVATE_LOCATOR"}}}""");
        await using var evaluation = await builder.EvaluateConfigurationAsync(new(document.ToJsonString(),
            readEnvironment: (_, _) => { reads++; return ValueTask.FromResult<string?>(null); }), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        var module = Assert.Single(lease.Discovery!.Capture().Observation!.Modules, item => item.Id == "protocol");
        Assert.Equal("disabled", module.Readiness);
        Assert.Equal(4, module.Options.Length);
        Assert.Equal(0, checks);
        Assert.Equal(0, reads);
        Assert.Null(ConfiguredFixtures.ProtocolDelivered);
        Assert.DoesNotContain("protocol", LifecycleFixtures.Controls.Keys);
        Assert.All(module.Options.Where(option => option.Secret), option =>
        { Assert.Null(option.PublicDefault); Assert.Null(option.AllowedValues); });
    }

    [Theory]
    [InlineData("missing", false)]
    [InlineData("missing", true)]
    [InlineData("invalid", false)]
    [InlineData("invalid", true)]
    [InlineData("secret", false)]
    [InlineData("secret", true)]
    [InlineData("range", false)]
    [InlineData("range", true)]
    public async Task Enabled_counterparts_preserve_active_validation_and_secret_gates(string failure, bool enabled)
    {
        ConfiguredFixtures.Reset();
        var reads = 0;
        var checks = 0;
        var declaration = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Configuration = ConfiguredFixtures.Contract.Fields.Select(field => new ConfigurationRequirement
            { Key = field.Key, Required = field.Required, SecretReference = field.Type == HoardOptionType.Secret, Description = "Unapproved" }).ToImmutableArray(),
            Compatibility = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol).Compatibility with
            { HostRange = failure == "range" ? "[9.0.0,10.0.0)" : "[0.1.0,0.2.0)" }
        };
        var builder = ConfiguredFixtures.Registry().AddModule<LifecycleFixtures.ProtocolProvider>(declaration)
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, ConfiguredFixtures.ConfiguredProtocolModule>()
            .AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(ConfiguredFixtures.Contract, (_, _) =>
            { checks++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); })
            .AddHoardDiscovery(new("fixture", "0.1.0", "complete"), new());
        var root = System.Text.Json.Nodes.JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        if (enabled) { root["enabledmodules"]!.AsArray().Add("protocol"); }
        if (failure != "missing")
        {
            root["modules"]!["protocol"] = System.Text.Json.Nodes.JsonNode.Parse(
                """{"optionsversion":1,"options":{"label":"valid","credential":{"kind":"env","target":"INVENTED_DISCOVERY_PRIVATE_LOCATOR"}}}""");
            if (failure == "invalid") { root["modules"]!["protocol"]!["options"]!["label"] = ""; }
        }
        await using var evaluation = await builder.EvaluateConfigurationAsync(new(root.ToJsonString(),
            readEnvironment: (_, _) => { reads++; return ValueTask.FromResult<string?>(null); }), LifecycleFixtures.Versions, new());
        Assert.Equal(enabled ? HoardConfigurationOutcome.Failed : HoardConfigurationOutcome.Validated, evaluation.Outcome);
        Assert.Null(ConfiguredFixtures.ProtocolDelivered);
        Assert.DoesNotContain("protocol", LifecycleFixtures.Controls.Keys);
        Assert.Equal(enabled && failure == "secret" ? 1 : 0, reads);
        if (!enabled)
        {
            Assert.Equal(0, checks);
            await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            Assert.Equal("disabled", lease.Discovery!.Capture().Observation!.Modules.Single(module => module.Id == "protocol").Readiness);
        }
    }
}
