using System.Collections.Immutable;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class ConfiguredCompositionTests
{
    [Theory]
    [InlineData("label", HoardConfigurationSource.Defaults)]
    [InlineData("label", HoardConfigurationSource.File)]
    [InlineData("label", HoardConfigurationSource.Environment)]
    [InlineData("label", HoardConfigurationSource.CommandLine)]
    [InlineData("count", HoardConfigurationSource.Defaults)]
    [InlineData("count", HoardConfigurationSource.File)]
    [InlineData("count", HoardConfigurationSource.Environment)]
    [InlineData("count", HoardConfigurationSource.CommandLine)]
    public async Task Declared_option_rules_keep_effective_field_source_and_safe_action(string field, HoardConfigurationSource source)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        foreach (var rejected in new[] { true, false })
        {
            var calls = 0;
            var reads = 0;
            var builder = ConfiguredFixtures.Registry((context, _) =>
            {
                calls++;
                Assert.Equal(HoardOptionCheckPhase.Public, context.Phase);
                return ValueTask.FromResult(rejected ? new HoardOptionCheckResult([new(field, "paired")])
                    : HoardOptionCheckResult.Accepted);
            });
            var defaults = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
            defaults["modules"]!["metadata"]!["options"]!["credential"] =
                new JsonObject { ["kind"] = "env", ["target"] = ConfigurationTestHarness.Locator };
            var overlay = new JsonObject
            {
                ["modules"] = new JsonObject
                {
                    ["metadata"] = new JsonObject
                    {
                        ["options"] = new JsonObject
                        { [field] = field == "label" ? JsonValue.Create("second") : JsonValue.Create(4) }
                    }
                }
            };
            if (source == HoardConfigurationSource.Defaults)
            { defaults["modules"]!["metadata"]!["options"]![field] = overlay["modules"]!["metadata"]!["options"]![field]!.DeepClone(); }
            if (source == HoardConfigurationSource.File) { overlay["configurationversion"] = 1; }
            var environment = source == HoardConfigurationSource.Environment
                ? new Dictionary<string, string> { ["HOARD_CONFIG"] = overlay.ToJsonString() } : [];
            var arguments = source == HoardConfigurationSource.CommandLine
                ? new[] { $"--hoard:modules:metadata:options:{field}=" + overlay["modules"]!["metadata"]!["options"]![field]!.ToJsonString() } : [];
            await using var result = await builder.EvaluateConfigurationAsync(new(defaults.ToJsonString(),
                explicitFile: source == HoardConfigurationSource.File ? "/invented/options-file" : null,
                environment: environment, arguments: arguments, readFile: (_, _) => ValueTask.FromResult(overlay.ToJsonString()),
                readEnvironment: (_, _) => { reads++; return ValueTask.FromResult<string?>(null); }), LifecycleFixtures.Versions, new());
            Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
            Assert.Null(result.Configuration);
            Assert.Equal(1, calls);
            if (rejected)
            {
                Assert.Equal(0, reads);
                var diagnostic = Assert.Single(result.Report.Diagnostics);
                Assert.Equal(HoardConfigurationRule.CheckFailure, diagnostic.Rule);
                Assert.Equal(HoardConfigurationPhase.PublicOptions, diagnostic.Phase);
                Assert.Equal("metadata", diagnostic.Owner);
                Assert.Equal($"modules:metadata:options:{field}", diagnostic.Setting);
                Assert.Equal(source, diagnostic.Source);
                Assert.Equal("paired", JsonSerializer.SerializeToElement(diagnostic).GetProperty("OptionRule").GetString());
                Assert.Contains("declared option rule", diagnostic.CorrectiveAction, StringComparison.Ordinal);
            }
            else
            {
                Assert.Equal(1, reads);
                Assert.Contains(result.Report.Diagnostics, d => d.Rule == HoardConfigurationRule.SecretUnavailable);
            }
            Assert.Empty(LifecycleFixtures.Controls);
            Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(result));
            Assert.DoesNotContain(ConfigurationTestHarness.Locator, JsonSerializer.Serialize(result));
            harness.AssertNoPayload("/invented/options-file");
        }
    }

    [Theory]
    [InlineData(HoardConfigurationSource.Environment)]
    [InlineData(HoardConfigurationSource.CommandLine)]
    public async Task Unsupported_active_option_version_keeps_its_explicit_setting_source(HoardConfigurationSource source)
    {
        ConfiguredFixtures.Reset();
        foreach (var version in new[] { 2, 1 })
        {
            var calls = 0;
            var builder = ConfiguredFixtures.Registry((_, _) =>
            { calls++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); });
            var environment = source == HoardConfigurationSource.Environment
                ? new Dictionary<string, string>
                { ["HOARD_CONFIG"] = JsonSerializer.Serialize(new { modules = new { metadata = new { optionsversion = version } } }) } : [];
            var arguments = source == HoardConfigurationSource.CommandLine
                ? new[] { $"--hoard:modules:metadata:optionsversion={version}" } : [];
            await using var result = await builder.EvaluateConfigurationAsync(new(ConfiguredFixtures.Defaults,
                environment: environment, arguments: arguments), LifecycleFixtures.Versions, new());
            Assert.Equal(version == 1 ? HoardConfigurationOutcome.Validated : HoardConfigurationOutcome.Failed, result.Outcome);
            if (version == 2)
            {
                Assert.Equal(0, calls);
                var diagnostic = Assert.Single(result.Report.Diagnostics);
                Assert.Equal(HoardConfigurationRule.UnsupportedVersion, diagnostic.Rule);
                Assert.Equal("modules:metadata:optionsversion", diagnostic.Setting);
                Assert.Equal(source, diagnostic.Source);
                Assert.Equal("metadata", diagnostic.Owner);
                Assert.Null(result.Configuration);
            }
            Assert.Empty(LifecycleFixtures.Controls);
        }
    }

    [Fact]
    public async Task Accepted_owner_values_enter_the_existing_lease_before_services()
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry();
        await using var evaluation = await ConfiguredFixtures.Evaluate(builder);
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
        Assert.Empty(LifecycleFixtures.Controls);
        await using var lease = await builder.ComposeHoardModulesAsync(Assert.IsType<HoardValidatedConfiguration>(evaluation.Configuration));
        Assert.Equal("first", ConfiguredFixtures.Delivered!.GetString("label"));
        Assert.Equal(3, ConfiguredFixtures.Delivered.GetInteger("count"));
        Assert.Equal(new[] { "construct", "options", "services" }, LifecycleFixtures.For("metadata").Calls);
        Assert.IsAssignableFrom<IHoardLifecycle>(lease.Lifecycle);
    }

    [Theory]
    [InlineData("unknown")]
    [InlineData("identity")]
    [InlineData("capability")]
    [InlineData("version")]
    public async Task Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids(string defect)
    {
        ConfiguredFixtures.Reset();
        var calls = 0;
        var builder = ConfiguredFixtures.Registry((_, _) =>
        { calls++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); });
        var document = JsonNode.Parse(ConfiguredFixtures.Defaults)!.AsObject();
        if (defect == "unknown") { document["enabledmodules"]!.AsArray().Add("invented-private-id"); }
        if (defect == "identity") { document["identitymodules"]!.AsArray().Add("invented-private-id"); }
        if (defect == "capability")
        {
            document["requiredcapabilities"] = JsonNode.Parse(
                """[{"module":"invented-private-id","id":"invented-private-id","range":"[1.0.0]","allowprerelease":false}]""");
        }
        var versions = defect == "version" ? new HoardPlatformVersions("9.0.0", "0.1.0") : LifecycleFixtures.Versions;
        await using var result = await builder.EvaluateConfigurationAsync(new(document.ToJsonString()), versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Null(result.Configuration);
        Assert.Equal(0, calls);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.DoesNotContain("invented-private-id", JsonSerializer.Serialize(result));
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("range")]
    [InlineData("version")]
    [InlineData("address")]
    [InlineData("callback")]
    [InlineData("malformed")]
    [InlineData("adapter")]
    public async Task Active_option_failures_precede_every_secret_read_and_construction(string defect)
    {
        ConfiguredFixtures.Reset();
        var reads = 0;
        var builder = ConfiguredFixtures.Registry((context, _) => ValueTask.FromResult(defect switch
        {
            "callback" => new HoardOptionCheckResult([new("label", "paired")]),
            "malformed" => new HoardOptionCheckResult([new("private-field", "private-rule")]),
            _ => HoardOptionCheckResult.Accepted
        }));
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!.AsObject();
        var module = root["modules"]!["metadata"]!.AsObject();
        var options = module["options"]!.AsObject();
        options["credential"] = JsonNode.Parse("""{"kind":"env","target":"INVENTED_CONFIGURATION_SECRET"}""");
        if (defect == "missing") { options.Remove("label"); }
        if (defect == "range") { options["count"] = 11; }
        if (defect == "version") { module["optionsversion"] = 2; }
        if (defect == "address") { options["address"] = "file:///not-http"; }
        if (defect == "adapter")
        {
            var association = builder.Services.Single(d => d.ServiceType == typeof(HoardModuleLifecycleRegistration)
                && ((HoardModuleLifecycleRegistration)d.ImplementationInstance!).ProviderType == typeof(LifecycleFixtures.MetadataProvider));
            builder.Services.Remove(association);
            builder.AddModuleLifecycle<LifecycleFixtures.MetadataProvider, LifecycleFixtures.MetadataModule>();
        }
        await using var result = await builder.EvaluateConfigurationAsync(new(root.ToJsonString(),
            readEnvironment: (_, _) => { reads++; return ValueTask.FromResult<string?>("unused"); }), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Null(result.Configuration);
        Assert.Equal(0, reads);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.DoesNotContain("private-field", JsonSerializer.Serialize(result));
        Assert.DoesNotContain("private-rule", JsonSerializer.Serialize(result));
    }

    [Fact]
    public async Task Disabled_semantic_failures_and_unavailable_references_do_no_work()
    {
        ConfiguredFixtures.Reset();
        var calls = 0;
        var builder = ConfiguredFixtures.Registry();
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Configuration = [new() { Key = "credential", Required = true, SecretReference = true, Description = "Fixture" }],
            Compatibility = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol).Compatibility with { HostRange = "[9.0.0]" }
        }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
          .AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(new(1, [new("credential", HoardOptionType.Secret, true)]),
              (_, _) => { calls++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); });
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        root["modules"]!["protocol"] = JsonNode.Parse(
            """{"optionsversion":99,"options":{"credential":{"kind":"file","target":"/invented/absent"}}}""");
        await using var result = await ConfiguredFixtures.Evaluate(builder, root.ToJsonString());
        Assert.Equal(HoardConfigurationOutcome.Validated, result.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(result.Configuration!);
        Assert.Equal(0, calls);
        Assert.DoesNotContain("protocol", LifecycleFixtures.Controls.Keys);
    }

    [Fact]
    public async Task Proof_rejects_foreign_changed_disposed_and_duplicate_consumption_before_construction()
    {
        foreach (var defect in new[] { "foreign", "service", "contract", "disposed" })
        {
            ConfiguredFixtures.Reset();
            var builder = ConfiguredFixtures.Registry();
            await using var result = await ConfiguredFixtures.Evaluate(builder);
            if (defect == "service") { builder.Services.AddSingleton(new object()); }
            if (defect == "contract") { builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(ConfiguredFixtures.Contract); }
            if (defect == "disposed") { await result.DisposeAsync(); }
            var target = defect == "foreign" ? ConfiguredFixtures.Registry() : builder;
            await Assert.ThrowsAsync<HoardLifecycleException>(() => target.ComposeHoardModulesAsync(result.Configuration!));
            Assert.Empty(LifecycleFixtures.Controls);
        }
        ConfiguredFixtures.Reset();
        var owner = ConfiguredFixtures.Registry();
        await using var proof = await ConfiguredFixtures.Evaluate(owner);
        await using var winner = await owner.ComposeHoardModulesAsync(proof.Configuration!);
        await Assert.ThrowsAsync<HoardLifecycleException>(() => owner.ComposeHoardModulesAsync(proof.Configuration!));
        Assert.Equal(1, LifecycleFixtures.For("metadata").Constructors);
    }

    [Fact]
    public async Task Legacy_compose_cannot_bypass_opt_in_and_cancelled_consume_constructs_nothing()
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry();
        var legacy = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        var failure = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(legacy));
        Assert.Contains(failure.Diagnostics, d => d.RuleCode == "ConfigurationRequired");
        await using var evaluation = await ConfiguredFixtures.Evaluate(builder);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => builder.ComposeHoardModulesAsync(evaluation.Configuration!, cancelled.Token));
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Thrown_configured_delivery_uses_existing_safe_lifecycle_failure()
    {
        ConfiguredFixtures.Reset();
        ConfiguredFixtures.OptionsHook = _ => throw new InvalidOperationException(ConfigurationTestHarness.Credential);
        var builder = ConfiguredFixtures.Registry();
        await using var result = await ConfiguredFixtures.Evaluate(builder);
        var failure = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(result.Configuration!));
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(failure.Diagnostics));
        Assert.DoesNotContain("services", LifecycleFixtures.For("metadata").Calls);
    }

    [Theory]
    [InlineData("version", "metadata", "compatible versions")]
    [InlineData("cardinality", "configuration", "exactly one authoritative")]
    [InlineData("dependency", "metadata", "required dependency")]
    public async Task Composition_diagnostics_preserve_closed_reason_known_owner_source_and_remap_dependency_paths(
        string defect, string owner, string action)
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry(metadataDependsOnArtifact: defect == "dependency");
        if (defect == "dependency")
        {
            var descriptor = builder.Services.Single(d => d.ServiceType == typeof(HoardModuleRegistration)
                && ((HoardModuleRegistration)d.ImplementationInstance!).ProviderType == typeof(LifecycleFixtures.MetadataProvider));
            var declaration = ((HoardModuleRegistration)descriptor.ImplementationInstance!).Declaration;
            builder.Services.Remove(descriptor);
            builder.AddModule<LifecycleFixtures.MetadataProvider>(declaration with
            {
                Dependencies = [new() { ModuleId = "invented-private-dependency", VersionRange = "[0.1.0]",
                    Optional = false, AllowPrerelease = false }]
            });
        }
        var enabled = defect == "cardinality" ? """["metadata"]""" : """["metadata","artifact"]""";
        await using var result = await builder.EvaluateConfigurationAsync(new(ConfiguredFixtures.Defaults,
            arguments: [$"--hoard:enabledmodules={enabled}"]),
            defect == "version" ? new("9.0.0", "0.1.0") : LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Contains(result.Report.Diagnostics, diagnostic => diagnostic.Owner == owner
            && diagnostic.Source == HoardConfigurationSource.CommandLine && diagnostic.Setting == "enabledmodules"
            && diagnostic.CorrectiveAction.Contains(action, StringComparison.Ordinal));
        var safe = JsonSerializer.Serialize(result.Report);
        Assert.DoesNotContain("invented-private-dependency", safe);
        if (defect == "dependency") { Assert.Contains("unknown-module-2", safe); }
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Multiple_protocols_and_identities_use_the_real_gate_activation_order()
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol))
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
            .AddModule<ConfiguredFixtures.SecondProtocol>(LifecycleFixtures.Declaration("protocol-two", ModuleCategory.Protocol))
            .AddModuleLifecycle<ConfiguredFixtures.SecondProtocol, ConfiguredFixtures.SecondProtocolModule>()
            .AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity))
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>()
            .AddModule<ConfiguredFixtures.SecondIdentity>(LifecycleFixtures.Declaration("identity-two", ModuleCategory.Identity))
            .AddModuleLifecycle<ConfiguredFixtures.SecondIdentity, ConfiguredFixtures.SecondIdentityModule>();
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        root["enabledmodules"] = new JsonArray("metadata", "artifact", "protocol", "protocol-two", "identity", "identity-two");
        root["identitymodules"] = new JsonArray("identity", "identity-two");
        var expected = builder.ValidateComposition(LifecycleFixtures.Selection("protocol", "protocol-two", "identity", "identity-two"),
            LifecycleFixtures.Versions, new()).Composition!;
        await using var result = await ConfiguredFixtures.Evaluate(builder, root.ToJsonString());
        Assert.Equal(HoardConfigurationOutcome.Validated, result.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(result.Configuration!);
        Assert.Equal(expected.ActivationOrder.ToArray(), lease.Composition.ActivationOrder.ToArray());
        Assert.Equal(6, LifecycleFixtures.Controls.Count);
        Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Constructors));
    }

    [Theory]
    [InlineData("absent-optional", true)]
    [InlineData("disabled-optional", true)]
    [InlineData("enabled-compatible", true)]
    [InlineData("enabled-incompatible", false)]
    [InlineData("missing-required", false)]
    [InlineData("cycle", false)]
    [InlineData("prerelease-permitted", true)]
    [InlineData("prerelease-forbidden", false)]
    [InlineData("malformed-declaration", false)]
    public async Task Configured_gate_preserves_actual_optional_dependency_cycle_prerelease_and_declaration_outcomes(
        string scenario, bool accepted)
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry();
        var enabled = scenario is "enabled-compatible" or "enabled-incompatible" or "cycle";
        if (enabled || scenario == "disabled-optional")
        {
            builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            {
                Version = scenario is "enabled-incompatible" or "disabled-optional" ? "0.2.0" : "0.1.0",
                Dependencies = scenario == "cycle"
                    ? [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }] : []
            }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        }
        if (!scenario.StartsWith("prerelease", StringComparison.Ordinal) && scenario != "malformed-declaration")
        {
            Alter("artifact", declaration => declaration with
            {
                Dependencies = [new() { ModuleId = "protocol", VersionRange = "[0.1.0]",
                    Optional = scenario != "missing-required", AllowPrerelease = false }]
            });
        }
        var versions = LifecycleFixtures.Versions;
        if (scenario.StartsWith("prerelease", StringComparison.Ordinal))
        {
            versions = new("0.1.0-beta", "0.1.0");
            foreach (var id in new[] { "metadata", "artifact" })
            {
                Alter(id, declaration => declaration with
                {
                    Compatibility = declaration.Compatibility with
                    { HostRange = "[0.1.0-beta,0.2.0)", AllowPrereleaseHost = scenario == "prerelease-permitted" }
                });
            }
        }
        if (scenario == "malformed-declaration") { Alter("artifact", declaration => declaration with { Version = "not-a-version" }); }
        var selection = enabled ? LifecycleFixtures.Selection("protocol") : LifecycleFixtures.Selection();
        var expected = builder.ValidateComposition(selection, versions, new());
        Assert.Equal(accepted, expected.Composition is not null);
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        if (enabled) { root["enabledmodules"]!.AsArray().Add("protocol"); }
        await using var actual = await builder.EvaluateConfigurationAsync(new(root.ToJsonString()), versions, new());
        Assert.Equal(accepted ? HoardConfigurationOutcome.Validated : HoardConfigurationOutcome.Failed, actual.Outcome);
        Assert.Equal(expected.Diagnostics.Select(d => d.RuleCode).Order(StringComparer.Ordinal).ToArray(),
            actual.Report.Diagnostics.Select(d => d.CompositionRule?.ToString()).Order(StringComparer.Ordinal).ToArray());
        Assert.Empty(LifecycleFixtures.Controls);

        void Alter(string id, Func<ModuleDescriptor, ModuleDescriptor> change)
        {
            var descriptor = builder.Services.Single(d => d.ServiceType == typeof(HoardModuleRegistration)
                && ((HoardModuleRegistration)d.ImplementationInstance!).Declaration.Id == id);
            var registration = (HoardModuleRegistration)descriptor.ImplementationInstance!;
            builder.Services[builder.Services.IndexOf(descriptor)] = ServiceDescriptor.Singleton(
                registration with { Declaration = change(registration.Declaration) });
        }
    }

    [Theory]
    [InlineData("allowed", false)]
    [InlineData("allowed", true)]
    [InlineData("range", false)]
    [InlineData("range", true)]
    public async Task Effective_allowed_values_and_ranges_reject_without_overrides_but_ignore_discarded_semantic_errors(
        string rule, bool overridden)
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry();
        builder.Services.Remove(builder.Services.Single(d => d.ServiceType == typeof(ConfigurationRegistration)));
        builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(new(1,
            ConfiguredFixtures.Contract.Fields.Select(field => field.Key == "label"
                ? field with { AllowedValues = ["first", "second"] } : field), ["paired"]));
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        if (rule == "allowed") { root["modules"]!["metadata"]!["options"]!["label"] = "not-listed"; }
        else { root["modules"]!["metadata"]!["options"]!["count"] = 0; }
        string[] arguments = !overridden ? [] : rule == "allowed"
            ? ["--hoard:modules:metadata:options:label=\"second\""]
            : ["--hoard:modules:metadata:options:count=5"];
        await using var result = await builder.EvaluateConfigurationAsync(new(root.ToJsonString(), arguments: arguments),
            LifecycleFixtures.Versions, new());
        Assert.Equal(overridden ? HoardConfigurationOutcome.Validated : HoardConfigurationOutcome.Failed, result.Outcome);
        if (!overridden) { Assert.Contains(result.Report.Diagnostics, d => d.Rule == HoardConfigurationRule.InvalidOption); }
        Assert.Empty(LifecycleFixtures.Controls);
    }
}

internal static class ConfiguredFixtures
{
    internal const string Defaults = """
        {"configurationversion":1,"enabledmodules":["metadata","artifact"],
         "metadatamodule":"metadata","artifactmodule":"artifact","identitymodules":[],"requiredcapabilities":[],
         "modules":{"metadata":{"optionsversion":1,"options":{"label":"first","count":3}}}}
        """;
    internal static HoardModuleOptions? Delivered;
    internal static HoardModuleOptions? ProtocolDelivered;
    internal static Action<HoardModuleOptions>? OptionsHook;
    internal static HoardModuleConfiguration Contract => new(1,
        [new("label", HoardOptionType.String, true) { MinimumLength = 1, MaximumLength = 16 },
         new("count", HoardOptionType.Integer) { Minimum = 1, Maximum = 10 },
         new("address", HoardOptionType.Address), new("credential", HoardOptionType.Secret)], ["paired"]);
    internal static void Reset()
    { LifecycleFixtures.Reset(); Delivered = null; ProtocolDelivered = null; OptionsHook = null; }
    internal static HoardBuilder Registry(HoardOptionValidator? validator = null, IServiceCollection? services = null,
        bool metadataDependsOnArtifact = false)
    {
        var builder = (services ?? new ServiceCollection()).AddHoard();
        var declaration = LifecycleFixtures.Declaration("metadata", ModuleCategory.Metadata) with
        {
            Dependencies = metadataDependsOnArtifact
                ? [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }] : [],
            Configuration = Contract.Fields.Select(f => new ConfigurationRequirement
            { Key = f.Key, Required = f.Required, SecretReference = f.Type == HoardOptionType.Secret, Description = "Fixture field" }).ToImmutableArray()
        };
        return builder.AddModule<LifecycleFixtures.MetadataProvider>(declaration)
            .AddModuleLifecycle<LifecycleFixtures.MetadataProvider, ConfiguredMetadataModule>()
            .AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(Contract, validator)
            .AddModule<LifecycleFixtures.ArtifactProvider>(LifecycleFixtures.Declaration("artifact", ModuleCategory.Artifact))
            .AddModuleLifecycle<LifecycleFixtures.ArtifactProvider, LifecycleFixtures.ArtifactModule>();
    }
    internal static Task<HoardConfigurationEvaluation> Evaluate(HoardBuilder builder, string? document = null) =>
        builder.EvaluateConfigurationAsync(new(document ?? Defaults), LifecycleFixtures.Versions, new());
    public sealed class ConfiguredMetadataModule() : LifecycleFixtures.Module("metadata"), IHoardConfiguredModule
    {
        public void ConfigureOptions(HoardModuleOptions options)
        {
            Delivered = options;
            lock (LifecycleFixtures.For("metadata").Calls) { LifecycleFixtures.For("metadata").Calls.Add("options"); }
            OptionsHook?.Invoke(options);
        }
    }
    public sealed class SecondProtocol : Hoard.Abstractions.Providers.IProtocolProvider;
    public sealed class SecondIdentity : Hoard.Abstractions.Providers.IIdentityProvider;
    public sealed class SecondProtocolModule() : LifecycleFixtures.Module("protocol-two");
    public sealed class SecondIdentityModule() : LifecycleFixtures.Module("identity-two");
    public sealed class ConfiguredProtocolModule() : LifecycleFixtures.Module("protocol"), IHoardConfiguredModule
    {
        public void ConfigureOptions(HoardModuleOptions options) => ProtocolDelivered = options;
    }
}
