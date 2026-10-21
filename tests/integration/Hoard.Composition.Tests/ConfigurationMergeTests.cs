using Hoard.Hosting.Configuration;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationMergeTests
{
    [Fact]
    public async Task Arrays_replace_options_merge_and_secret_references_replace_atomically()
    {
        const string defaults = """
            {"configurationversion":1,"enabledmodules":["metadata","artifact","protocol"],
             "metadatamodule":"metadata","artifactmodule":"artifact","identitymodules":[],
             "requiredcapabilities":[{"module":"protocol","id":"capability","range":"*","allowprerelease":false}],
             "modules":{"protocol":{"optionsversion":1,"options":{"count":-5,"label":"retained",
               "credential":{"kind":"file","target":"/unread-disabled-secret"}}}}}
            """;
        var input = new HoardConfigurationInput(defaults, environment: new Dictionary<string, string>
        {
            ["HOARD_CONFIG"] = """
                {"enabledmodules":["metadata","artifact"],"requiredcapabilities":[],
                 "modules":{"protocol":{"options":{"count":7,"credential":{"kind":"env","target":"INVENTED_REFERENCE"}}}}}
                """
        });
        var result = await ConfigurationSourceResolution.InspectAsync(ConfigurationStructureTests.Registry(), input);
        Assert.Equal(new[] { "metadata", "artifact" }, result.Get<string[]>("enabledmodules"));
        Assert.Empty(result.Get<Hoard.Hosting.Composition.HoardRequiredCapability[]>("requiredcapabilities"));
        Assert.Equal(7L, result.Get<long>("modules:protocol:options:count"));
        Assert.Equal("retained", result.Get<string>("modules:protocol:options:label"));
        Assert.Equal(1L, result.Get<long>("modules:protocol:optionsversion"));
        Assert.Equal("env", result.Get<SecretReference>("modules:protocol:options:credential").Kind);
        Assert.Equal("INVENTED_REFERENCE", result.Get<SecretReference>("modules:protocol:options:credential").Target);
    }

    [Fact]
    public async Task Explicit_emptiness_is_not_a_missing_value_or_an_informative_default()
    {
        var result = await ConfigurationSourceResolution.InspectAsync(ConfigurationStructureTests.Registry(),
            new(ConfigurationFixtures.Defaults, environment: new Dictionary<string, string>
            { ["HOARD_CONFIG"] = """{"enabledmodules":[],"artifactmodule":"","modules":{"protocol":{"options":{"label":""}}}}""" }));
        Assert.Empty(result.Get<string[]>("enabledmodules"));
        Assert.Equal("", result.Get<string>("artifactmodule"));
        Assert.Equal("", result.Get<string>("modules:protocol:options:label"));
        Assert.False(result.Assignments.ContainsKey("modules:protocol:options:count"));
    }
}
