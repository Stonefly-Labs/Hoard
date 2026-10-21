using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationContractTests
{
    [Fact]
    public void Registration_is_inert_and_metadata_is_defensively_copied()
    {
        LifecycleFixtures.Reset();
        var fields = new[] { new HoardOptionField("label", HoardOptionType.String, required: true) };
        var contract = new HoardModuleConfiguration(1, fields, ["paired"]);
        var builder = LifecycleFixtures.Registry();
        var calls = 0;
        builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(contract, (_, _) =>
        {
            calls++;
            throw new InvalidOperationException(ConfigurationTestHarness.Credential);
        });
        fields[0] = new("replacement", HoardOptionType.String);
        Assert.Equal("label", Assert.Single(contract.Fields).Key);
        Assert.Equal(0, calls);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, contract.ToString());
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("duplicate")]
    [InlineData("orphan")]
    [InlineData("flags")]
    [InlineData("collision")]
    public async Task Invalid_associations_fail_without_callbacks_or_construction(string defect)
    {
        LifecycleFixtures.Reset();
        var services = new ServiceCollection();
        var builder = services.AddHoard();
        var declaration = LifecycleFixtures.Declaration("metadata", ModuleCategory.Metadata) with
        {
            Configuration = [new() { Key = "label", Description = "Reviewed label", Required = true, SecretReference = false }]
        };
        builder.AddModule<LifecycleFixtures.MetadataProvider>(declaration)
            .AddModuleLifecycle<LifecycleFixtures.MetadataProvider, LifecycleFixtures.MetadataModule>()
            .AddModule<LifecycleFixtures.ArtifactProvider>(LifecycleFixtures.Declaration("artifact", ModuleCategory.Artifact))
            .AddModuleLifecycle<LifecycleFixtures.ArtifactProvider, LifecycleFixtures.ArtifactModule>();
        var field = new HoardOptionField("label", HoardOptionType.String, required: defect != "flags");
        var contract = new HoardModuleConfiguration(1, defect == "collision" ? [field, field with { Key = "LABEL" }] : [field]);
        var calls = 0;
        HoardOptionValidator validator = (_, _) => { calls++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); };
        if (defect != "missing")
        { builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(contract, validator); }
        if (defect == "duplicate")
        { builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(contract, validator); }
        if (defect == "orphan")
        { builder.AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(new(1, []), validator); }
        await using var evaluation = await builder.EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, evaluation.Outcome);
        Assert.Null(evaluation.Configuration);
        Assert.Contains(evaluation.Report.Diagnostics, item => item.Rule is
            HoardConfigurationRule.MissingConfigurationContract or HoardConfigurationRule.InvalidConfigurationContract);
        Assert.Equal(0, calls);
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Private_inputs_and_options_do_not_serialize_values()
    {
        var input = new HoardConfigurationInput(ConfigurationTestHarness.Credential,
            environment: new Dictionary<string, string> { [ConfigurationTestHarness.Locator] = ConfigurationTestHarness.Credential });
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, input.ToString());
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(input));
        await using var evaluation = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            input, LifecycleFixtures.Versions, new());
        var output = JsonSerializer.Serialize(evaluation) + evaluation;
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, output);
        Assert.DoesNotContain(ConfigurationTestHarness.Locator, output);
        Assert.NotEqual(Guid.Empty, evaluation.Report.CorrelationId);
        Assert.All(evaluation.Report.Diagnostics, item => Assert.NotEmpty(item.CorrectiveAction));
        Assert.Empty(typeof(HoardValidatedConfiguration).GetConstructors());
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(double.PositiveInfinity)]
    [InlineData(double.NaN)]
    [InlineData(double.MaxValue)]
    [InlineData(double.Epsilon)]
    public async Task Invalid_host_budgets_fail_before_input_callbacks(double milliseconds)
    {
        var reads = 0;
        var options = new HoardConfigurationOptions { EvaluationTimeoutMilliseconds = milliseconds };
        await using var evaluation = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, explicitFile: "/unused",
                readFile: (_, _) => { reads++; throw new InvalidOperationException(); }),
            LifecycleFixtures.Versions, new(), options);
        Assert.Equal(HoardConfigurationOutcome.Failed, evaluation.Outcome);
        Assert.Equal(0, reads);
        Assert.Contains(evaluation.Report.Diagnostics, item => item.Rule == HoardConfigurationRule.InvalidBudget);
    }

    [Fact]
    public void Owner_options_keep_types_and_secrets_private_until_single_release()
    {
        var secret = new HoardSecretValue(ConfigurationTestHarness.Credential);
        var options = new HoardModuleOptions(new Dictionary<string, object>
        { ["label"] = "ordinary", ["enabled"] = true, ["count"] = 3L, ["credential"] = secret });
        var lease = new OwnerOptionsLease(options);
        Assert.Equal("ordinary", options.GetString("label"));
        Assert.True(options.GetBoolean("enabled"));
        Assert.Equal(3, options.GetInteger("count"));
        Assert.Throws<InvalidOperationException>(() => options.GetString("credential"));
        Assert.Throws<InvalidOperationException>(() => options.GetSecret("label"));
        Assert.Throws<InvalidOperationException>(() => options.GetString("missing"));
        Assert.Equal(ConfigurationTestHarness.Credential, options.GetSecret("credential").Reveal());
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(options) + options + secret);
        lease.Dispose();
        lease.Dispose();
        Assert.Throws<ObjectDisposedException>(() => secret.Reveal());
    }

    [Fact]
    public void Safe_diagnostics_cap_unknown_identities_without_reflecting_regex_valid_payloads()
    {
        var supervisor = new ConfigurationSupervisor(new() { MaximumDiagnostics = 3 }, CancellationToken.None);
        for (var index = 0; index < 5; index++)
        {
            Assert.Throws<ConfigurationFailure>(() => supervisor.Reject(HoardConfigurationRule.UnknownSetting,
                HoardConfigurationPhase.Structure, owner: "invented-credential", setting: "invented-locator"));
        }
        supervisor.Fail(HoardConfigurationRule.UnknownSetting);
        supervisor.Complete(false);
        supervisor.Dispose();
        Assert.Equal(3, supervisor.Snapshot.Diagnostics.Length);
        Assert.Equal(2, supervisor.Snapshot.OmittedCount);
        var output = JsonSerializer.Serialize(supervisor.Snapshot);
        Assert.DoesNotContain("invented-credential", output);
        Assert.DoesNotContain("invented-locator", output);
    }

    [Fact]
    public async Task Input_snapshots_stop_at_hard_bounds_before_exhausting_supplied_collections()
    {
        var enumerated = 0;
        IEnumerable<string> Arguments()
        {
            for (var index = 0; index < 5000; index++) { enumerated++; yield return "--unrelated"; }
        }
        var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults, arguments: Arguments());
        await using var result = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(input, LifecycleFixtures.Versions, new());
        Assert.Contains(result.Report.Diagnostics, item => item.Rule == HoardConfigurationRule.InputLimit);
        Assert.InRange(enumerated, 1, 4097);
        var entries = Enumerable.Range(0, 4097).ToDictionary(index => $"INVENTED_{index}", _ => "unused");
        await using var environment = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, environment: entries), LifecycleFixtures.Versions, new());
        Assert.Contains(environment.Report.Diagnostics, item => item.Rule == HoardConfigurationRule.InputLimit);
    }

    [Fact]
    public async Task Oversized_snapshot_argument_does_not_enumerate_following_inputs()
    {
        var enumerated = 0;
        IEnumerable<string> Arguments()
        {
            enumerated++; yield return "--hoard:" + new string('a', 1024 * 1024);
            enumerated++; yield return "--urls=http://unrelated.invalid";
        }
        await using var result = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, arguments: Arguments()), LifecycleFixtures.Versions, new());
        Assert.Contains(result.Report.Diagnostics, item => item.Rule == HoardConfigurationRule.InputLimit);
        Assert.Equal(1, enumerated);
    }

    [Fact]
    public void Descriptive_metadata_cannot_exhaust_an_unbounded_field_enumeration()
    {
        var count = 0;
        IEnumerable<HoardOptionField> Fields()
        {
            while (true) { count++; yield return new("label", HoardOptionType.String); }
        }
        var contract = new HoardModuleConfiguration(1, Fields());
        Assert.Equal(257, count);
        Assert.Equal(257, contract.Fields.Length);
    }
}

internal static class ConfigurationFixtures
{
    internal const string Defaults = """
        {"configurationversion":1,"enabledmodules":["metadata","artifact"],
         "metadatamodule":"metadata","artifactmodule":"artifact","identitymodules":[],"requiredcapabilities":[]}
        """;
}
