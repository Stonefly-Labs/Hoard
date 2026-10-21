using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationStructureTests
{
    internal static HoardBuilder Registry()
    {
        var builder = LifecycleFixtures.Registry();
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Configuration =
            [
                new() { Key = "count", Description = "Fixture integer", Required = false, SecretReference = false },
                new() { Key = "label", Description = "Fixture label", Required = false, SecretReference = false },
                new() { Key = "address", Description = "Fixture address", Required = false, SecretReference = false },
                new() { Key = "credential", Description = "Fixture credential", Required = false, SecretReference = true }
            ]
        }).AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(new(1,
        [
            new("count", HoardOptionType.Integer) { Minimum = 1, Maximum = 10 },
            new("label", HoardOptionType.String),
            new("address", HoardOptionType.Address),
            new("credential", HoardOptionType.Secret)
        ]));
        return builder;
    }

    [Theory]
    [InlineData("""{"artifactmodule":"artifact","ARTIFACTMODULE":"artifact"}""")]
    [InlineData("""{"artifactmodule":"artifact","artifact\u006dodule":"artifact"}""")]
    [InlineData("""{"enabledmodules":["metadata","metadata"]}""")]
    [InlineData("""{"requiredcapabilities":[{"module":"metadata","id":"capability","range":"[1,2)","allowprerelease":false},{"module":"metadata","id":"capability","range":"*","allowprerelease":false}]}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"count":null}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"count":"5"}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"count":9223372036854775808}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"label":{"nested":"invalid"}}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"unknown":"invented-configuration-credential"}}}}""")]
    [InlineData("""{"server":{"listen":"0.0.0.0"}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"address":"https://user:private@example.invalid"}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"address":"https://example.invalid/?private"}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"address":"https://example.invalid/#private"}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"credential":"literal"}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"credential":{"kind":"cloud","target":"invented"}}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"credential":{"kind":"env","target":"${INVENTED}"}}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"credential":{"kind":"file","target":"relative/path"}}}}}""")]
    [InlineData("""{"modules":{"protocol":{"options":{"credential":{"kind":"env","target":"INVENTED","extra":true}}}}}""")]
    [InlineData("""{"identitymodules":[],}""")]
    [InlineData("""{/*comment*/"identitymodules":[]}""")]
    public async Task Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden(string overlay)
    {
        var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
            environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = overlay },
            arguments: ["""--hoard:modules:protocol:options:count=5"""]);
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(), input));
    }

    [Fact]
    public async Task Canonical_keys_decode_before_duplicates_and_values_are_not_normalized()
    {
        var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
            environment: new Dictionary<string, string>
            { ["HOARD_CONFIG"] = """{"MODULES":{"PROTOCOL":{"OPTIONS":{"LaBeL":"Keep My Case","address":"https://example.invalid/public"}}}}""" });
        var resolved = await ConfigurationSourceResolution.InspectAsync(Registry(), input);
        Assert.Equal("Keep My Case", resolved.Get<string>("modules:protocol:options:label"));
        Assert.Equal("https://example.invalid/public", resolved.Get<string>("modules:protocol:options:address"));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(ConfigurationFixtures.Defaults, arguments: ["--hoard:artifactmodule=\"a\"", "--hoard:ARTIFACTMODULE=\"b\""])));
    }

    [Fact]
    public async Task Limits_are_applied_before_merge_to_discarded_inputs()
    {
        var options = new HoardConfigurationOptions { MaximumStringBytes = 32, MaximumDocumentBytes = 512 };
        var valid = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
            environment: new Dictionary<string, string>
            { ["HOARD_CONFIG"] = """{"modules":{"protocol":{"options":{"label":""" + "\"" + new string('a', 32) + "\"}}}}" });
        await ConfigurationSourceResolution.InspectAsync(Registry(), valid, options);
        var oversized = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
            environment: new Dictionary<string, string>
            { ["HOARD_CONFIG"] = """{"modules":{"protocol":{"options":{"label":""" + "\"" + new string('a', 33) + "\"}}}}" },
            arguments: ["""--hoard:modules:protocol:options:label="short" """.TrimEnd()]);
        await Assert.ThrowsAsync<ConfigurationFailure>(() =>
            ConfigurationSourceResolution.InspectAsync(Registry(), oversized, options));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(new string(' ', 513) + ConfigurationFixtures.Defaults), options));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(ConfigurationFixtures.Defaults), new() { MaximumAssignments = 2 }));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(ConfigurationFixtures.Defaults), new() { MaximumSelectionIds = 1 }));
    }

    [Fact]
    public async Task Known_field_failures_keep_safe_identity_but_unknown_names_are_not_reflected()
    {
        foreach (var (key, expected) in new[] { ("count", "modules:protocol:options:count"), ("invented-locator", "unknown-setting") })
        {
            await using var result = await Registry().EvaluateConfigurationAsync(
                new(ConfigurationFixtures.Defaults, environment: new Dictionary<string, string>
                { ["HOARD_CONFIG"] = "{\"modules\":{\"protocol\":{\"options\":{\"" + key + "\":\"invented-payload\"}}}}" }),
                LifecycleFixtures.Versions, new());
            var diagnostic = Assert.Single(result.Report.Diagnostics);
            Assert.Equal("protocol", diagnostic.Owner);
            Assert.Equal(expected, diagnostic.Setting);
            var output = System.Text.Json.JsonSerializer.Serialize(result);
            Assert.DoesNotContain("invented-locator", output);
            Assert.DoesNotContain("invented-payload", output);
        }
    }

    [Fact]
    public async Task Document_depth_assignment_and_selection_limits_have_exact_permitted_counterparts()
    {
        var padded = ConfigurationFixtures.Defaults.PadRight(512);
        await ConfigurationSourceResolution.InspectAsync(Registry(), new(padded),
            new() { MaximumDocumentBytes = 512, MaximumAssignments = 6 });
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(padded + " "), new() { MaximumDocumentBytes = 512 }));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(padded), new() { MaximumAssignments = 5 }));
        const string overlay = """{"modules":{"protocol":{"options":{"label":"public"}}}}""";
        var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
            environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = overlay });
        await ConfigurationSourceResolution.InspectAsync(Registry(), input, new() { MaximumDepth = 4, MaximumFieldsPerModule = 4 });
        await Assert.ThrowsAsync<ConfigurationFailure>(() =>
            ConfigurationSourceResolution.InspectAsync(Registry(), input, new() { MaximumDepth = 3 }));
        await Assert.ThrowsAsync<ConfigurationFailure>(() =>
            ConfigurationSourceResolution.InspectAsync(Registry(), input, new() { MaximumFieldsPerModule = 3 }));
        var selection = System.Text.Json.JsonSerializer.Serialize(new { enabledmodules = Enumerable.Range(0, 256).Select(index => $"fixture-{index}") });
        await ConfigurationSourceResolution.InspectAsync(Registry(),
            new(ConfigurationFixtures.Defaults, environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = selection }));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => ConfigurationSourceResolution.InspectAsync(Registry(),
            new(ConfigurationFixtures.Defaults, environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = selection }),
            new() { MaximumSelectionIds = 255 }));
    }

    [Fact]
    public async Task Utf8_string_and_private_locator_limits_apply_to_bytes_not_character_count()
    {
        foreach (var (field, value) in new[]
        {
            ("label", System.Text.Json.JsonSerializer.Serialize(new string('\u00e9', 8192))),
            ("credential", System.Text.Json.JsonSerializer.Serialize(new { kind = "file", target = "/" + new string('a', 16383) }))
        })
        {
            var prefix = "{\"modules\":{\"protocol\":{\"options\":{\"" + field + "\":";
            var input = new HoardConfigurationInput(ConfigurationFixtures.Defaults,
                environment: new Dictionary<string, string> { ["HOARD_CONFIG"] = prefix + value + "}}}}" });
            await ConfigurationSourceResolution.InspectAsync(Registry(), input);
            await Assert.ThrowsAsync<ConfigurationFailure>(() =>
                ConfigurationSourceResolution.InspectAsync(Registry(), input, new() { MaximumStringBytes = 16383 }));
        }
    }
}
