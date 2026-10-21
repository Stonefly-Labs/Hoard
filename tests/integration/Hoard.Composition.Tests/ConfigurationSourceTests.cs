using Hoard.Hosting.Configuration;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationSourceTests
{
    [Fact]
    public async Task Four_sources_are_explicit_deterministic_and_keep_winning_provenance()
    {
        await using var harness = new ConfigurationTestHarness();
        var file = harness.File("configuration.json", """{"configurationversion":1,"artifactmodule":"from-file"}""");
        var environment = new Dictionary<string, string> { ["HOARD_CONFIG"] = """{"artifactmodule":"from-environment"}""" };
        var arguments = new[] { """--hoard:artifactmodule="from-cli" """.TrimEnd(), "--urls=http://unrelated.invalid" };
        for (var repeat = 0; repeat < 3; repeat++)
        {
            var resolved = await ConfigurationSourceResolution.InspectAsync(
                LifecycleFixtures.Registry(), new(ConfigurationFixtures.Defaults, file, arguments, environment));
            Assert.Equal("from-cli", resolved.Get<string>("artifactmodule"));
            Assert.Equal(HoardConfigurationSource.CommandLine, resolved.Assignments["artifactmodule"].Source);
            Assert.Equal(HoardConfigurationSource.Defaults, resolved.Assignments["metadatamodule"].Source);
        }
        environment["HOARD_CONFIG"] = "changed";
        var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults, environment: new Dictionary<string, string>());
        var absent = await ConfigurationSourceResolution.InspectAsync(LifecycleFixtures.Registry(), input);
        Assert.Equal("artifact", absent.Get<string>("artifactmodule"));
    }

    [Theory]
    [InlineData("--hoard-file=")]
    [InlineData("--hoard-file=/absent", "--hoard-file=/also-absent")]
    [InlineData("--hoard-wrong")]
    [InlineData("--hoard:artifactmodule")]
    [InlineData("--hoard:modules={} ")]
    [InlineData("--hoard:artifactmodule=unquoted")]
    public async Task Malformed_reserved_arguments_fail_without_payloads(params string[] arguments)
    {
        var failure = await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(
            LifecycleFixtures.Registry(), new(ConfigurationFixtures.Defaults, arguments: arguments)));
        Assert.DoesNotContain("/absent", failure.ToString());
    }

    [Fact]
    public async Task Requested_files_empty_overlays_and_case_equivalent_overlay_names_are_not_absence()
    {
        foreach (var input in new[]
        {
            new HoardConfigurationInput(ConfigurationFixtures.Defaults, explicitFile: "/absent-configuration"),
            new HoardConfigurationInput(ConfigurationFixtures.Defaults, explicitFile: "/invented", arguments: ["--hoard-file=/another"]),
            new HoardConfigurationInput(ConfigurationFixtures.Defaults, environment: new Dictionary<string,string> { ["HOARD_CONFIG"] = "" }),
            new HoardConfigurationInput(ConfigurationFixtures.Defaults, environment: new Dictionary<string,string>
                { ["HOARD_CONFIG"] = "{}", ["hoard_config"] = "{}" })
        })
        {
            await Assert.ThrowsAsync<ConfigurationFailure>(() =>
                ConfigurationSourceResolution.InspectAsync(LifecycleFixtures.Registry(), input));
        }
    }
}
