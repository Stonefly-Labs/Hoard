using Hoard.Hosting.Configuration;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationVersionTests
{
    [Theory]
    [InlineData("{}")]
    [InlineData("""{"configurationversion":"1"}""")]
    [InlineData("""{"configurationversion":2}""")]
    [InlineData("""{"configurationversion":null}""")]
    [InlineData("""{"configurationversion":"fixture-v0"}""")]
    public async Task Each_document_requires_its_own_current_integer_version(string document)
    {
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(
            LifecycleFixtures.Registry(), new(document)));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(
            LifecycleFixtures.Registry(), new(ConfigurationFixtures.Defaults, explicitFile: "/invented",
                readFile: (_, _) => ValueTask.FromResult(document),
                environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = """{"artifactmodule":"artifact"}""" })));
    }

    [Fact]
    public async Task Overlays_cannot_override_or_repair_document_versions()
    {
        foreach (var input in new[]
        {
            new HoardConfigurationInput(ConfigurationFixtures.Defaults,
                arguments: ["--hoard:configurationversion=1"]),
            new HoardConfigurationInput(ConfigurationFixtures.Defaults,
                environment: new Dictionary<string,string> { ["HOARD_CONFIG"] = """{"configurationversion":1}""" })
        })
        {
            await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(
                LifecycleFixtures.Registry(), input));
        }
    }
}
