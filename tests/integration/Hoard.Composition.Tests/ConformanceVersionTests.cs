using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Fixtures.Conformance.Host;
using Hoard.Foundation.Tests;
using Hoard.Hosting.Composition;
using Xunit.Abstractions;

namespace Hoard.Composition.Tests;

public sealed class ConformanceVersionTests(ITestOutputHelper output)
{
    public static IEnumerable<object[]> Matrix() =>
        from axis in new[] { "host", "abstractions", "required", "optional" }
        from row in VersionFixtures.Rows
        select new object[] { axis, row.Id };

    [Theory]
    [MemberData(nameof(Matrix))]
    public void Runtime_matrix(string axis, string row)
    {
        var input = VersionFixtures.Rows.Single(item => item.Id == row);
        var (registry, result) = VersionFixtures.Evaluate(axis, input.Range, input.Candidate, input.Prerelease);
        Assert.Equal(input.Accepted, result.Composition is not null);
        Assert.All(registry.Probes.Values, probe => Assert.Equal(0, probe.Constructors));
        if (input.Accepted)
        {
            Assert.Empty(result.Diagnostics);
            Assert.Equal(axis is "required" or "optional" ? 1 : 0, result.Composition!.ActiveEdges.Length);
        }
        else
        {
            LifecycleFixtures.AssertSafe(result.Diagnostics);
            Assert.DoesNotContain("conformance-secret", JsonSerializer.Serialize(result.Diagnostics));
            Assert.Contains(result.Diagnostics, item => item.RuleCode is "UnsupportedPlatform" or "UnsupportedDependency" or "MalformedRegistry");
            var repair = VersionFixtures.Repair(row);
            var (repairedRegistry, repaired) = VersionFixtures.Evaluate(axis, repair.Range, repair.Candidate, repair.Prerelease);
            Assert.NotNull(repaired.Composition);
            Assert.Empty(repaired.Diagnostics);
            Assert.All(repairedRegistry.Probes.Values, probe => Assert.Equal(0, probe.Constructors));
            Assert.Equal(axis is "required" or "optional" ? 1 : 0, repaired.Composition.ActiveEdges.Length);
            output.WriteLine($"version/{axis}/{row}/repair: accepted=1; constructors=0; diagnostics=0; " +
                $"active-edges={repaired.Composition.ActiveEdges.Length}");
        }
        output.WriteLine($"version/{axis}/{row}: accepted={(result.Composition is null ? 0 : 1)}; constructors=0; diagnostics={result.Diagnostics.Length}");
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(false, false)]
    [InlineData(true, true)]
    public void Platform_prerelease_flags_are_independent(bool host, bool abstractions)
    {
        var registry = new CompositionFixtures.Registry();
        foreach (var id in new[] { "metadata", "artifact" })
        {
            registry.Replace(id, declaration => declaration with
            {
                Version = "0.1.0-beta.1",
                Compatibility = declaration.Compatibility with
                { AllowPrereleaseHost = host, AllowPrereleaseAbstractions = abstractions }
            });
        }
        var result = registry.Builder.ValidateComposition(CompositionFixtures.Selection(),
            new("0.1.1-rc.1", "0.1.1-rc.1"), new());
        Assert.Equal(host && abstractions, result.Composition is not null);
        Assert.All(registry.Probes.Values, probe => Assert.Equal(0, probe.Constructors));
        output.WriteLine($"version/platform-flags/{host}/{abstractions}: accepted={(result.Composition is null ? 0 : 1)}; constructors=0");
    }

    [Theory]
    [InlineData("absent")]
    [InlineData("registered-disabled")]
    public void Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability(string selection)
    {
        var (registry, result) = VersionFixtures.Evaluate("optional", "[0.1.0,0.2.0)", "9.0.0", false, selection);
        Assert.NotNull(result.Composition);
        Assert.Empty(result.Composition.ActiveEdges);
        Assert.Empty(result.Composition.SatisfiedCapabilities);
        Assert.DoesNotContain("protocol", result.Composition.EnabledModuleIds);
        var demanded = registry.Builder.ValidateComposition(CompositionFixtures.Selection() with
        { RequiredCapabilities = [new("protocol", "integration", "[0.1.0]", false)] }, CompositionFixtures.Versions, new());
        Assert.Null(demanded.Composition);
        Assert.Contains(demanded.Diagnostics, item => item.RuleCode == "UnsupportedCapability");
        output.WriteLine($"version/optional/{selection}: active-edges=0; capabilities=0; demanded-capability-rejections=1");
    }

    public static IEnumerable<object[]> Classifications()
    {
        yield return ["C-01", "host", "[1.2.0,2.0.0)", "1.4.0", false, "enabled", true];
        yield return ["C-02", "host", "[1.2.0,2.0.0)", "2.0.0", false, "enabled", false];
        yield return ["C-03", "host", "", "1.0.0", false, "enabled", false];
        yield return ["C-04", "host", "[0.1.0,0.2.0)", "0.2.0", false, "enabled", false];
        yield return ["C-07", "host", "[1.0.0,2.0.0)", "1.5.0-rc.1", false, "enabled", false];
        yield return ["C-08", "host", "[1.0.0,2.0.0)", "1.5.0-rc.1", true, "enabled", true];
        yield return ["C-09", "host", "[1.5.0,2.0.0)", "1.5.0-rc.1", true, "enabled", false];
        yield return ["C-10", "host", "[1.5.0-rc.1,1.5.0]", "1.5.0-rc.2", false, "enabled", false];
        yield return ["C-12", "host", "[1.2.3]", "1.2.3+build.7", false, "enabled", true];
        yield return ["C-13", "host", "(2.0.0,1.0.0]", "1.5.0", false, "enabled", false];
        yield return ["C-14", "required", "[1.0.0,2.0.0)", "1.5.0", false, "absent", false];
        yield return ["C-14-outside", "required", "[1.0.0,2.0.0)", "2.0.0", false, "enabled", false];
        yield return ["C-15", "optional", "[1.0.0,2.0.0)", "1.5.0", false, "absent", true];
        yield return ["C-19", "optional", "[1.0.0,2.0.0)", "1.5.0", false, "enabled", true];
        yield return ["C-20", "optional", "[1.0.0,2.0.0)", "2.0.0", false, "enabled", false];
        yield return ["C-21", "optional", "[1.0.0,2.0.0)", "1.5.0-rc.1", false, "enabled", false];
        yield return ["C-22", "optional", "[1.0.0,2.0.0)", "1.5.0-rc.1", true, "enabled", true];
        yield return ["C-23", "optional", "[1.0.0,2.0.0)", "2.0.0", false, "registered-disabled", true];
    }

    [Theory]
    [MemberData(nameof(Classifications))]
    public void Inherited_runtime_classification(string id, string axis, string range, string candidate,
        bool prerelease, string selection, bool accepted)
    {
        var (_, result) = VersionFixtures.Evaluate(axis, range, candidate, prerelease, selection);
        Assert.Equal(accepted, result.Composition is not null);
        if (accepted && axis is "optional" or "required")
        { Assert.Equal(selection == "enabled" ? 1 : 0, result.Composition!.ActiveEdges.Length); }
        output.WriteLine($"classification/{id}: accepted={(result.Composition is null ? 0 : 1)}; diagnostics={result.Diagnostics.Length}");
    }

    [Theory]
    [InlineData("C-11", true, false)]
    [InlineData("C-18", false, false)]
    public void Inherited_platform_flags_do_not_derive_from_module_version(string id, bool host, bool abstractions)
    {
        var registry = new CompositionFixtures.Registry();
        registry.Replace("metadata", declaration => declaration with
        {
            Version = id == "C-18" ? "0.1.0-beta.1" : "0.1.0",
            Compatibility = declaration.Compatibility with
            { AllowPrereleaseHost = host, AllowPrereleaseAbstractions = abstractions }
        });
        registry.Replace("artifact", declaration => declaration with
        { Compatibility = declaration.Compatibility with { AllowPrereleaseHost = true, AllowPrereleaseAbstractions = true } });
        var result = registry.Builder.ValidateComposition(CompositionFixtures.Selection(),
            new("0.1.1-rc.1", id == "C-11" ? "0.1.1-rc.1" : "0.1.0"), new());
        Assert.Null(result.Composition);
        Assert.Contains(result.Diagnostics, item => item.ModuleId == "metadata" && item.RuleCode == "UnsupportedPlatform");
        output.WriteLine($"classification/{id}: accepted=0; unsupported-platform={result.Diagnostics.Length}");
    }

    [Theory]
    [InlineData("C-05", "stable-major", "2.0.0")]
    [InlineData("C-06", "pre-1.0-minor", "0.2.0")]
    [InlineData("C-16", "stable-major", "2.0.0")]
    [InlineData("C-17", "stable-major", "2.0.0")]
    public void Inherited_release_classifier_is_policy_not_runtime_evidence(string id, string transition, string repairedVersion)
    {
        var example = ContractChangeExamples.All.Single(item => item.Id == id);
        Assert.False(example.ProposedReleaseValid);
        Assert.Equal(transition, example.RequiredTransition);
        Assert.True((example with { ProposedVersion = repairedVersion }).ProposedReleaseValid);
        Assert.NotEqual(example.OldRange, example.NewRange);
        Assert.All(new[] { example.ConsumerImpact, example.ImplementerImpact, example.BinaryImpact,
            example.BehaviorImpact, example.Migration, example.Qualification, example.Rollback }, Assert.NotEmpty);
        output.WriteLine($"classification/{id}: policy-invalid=1; repaired-policy-valid=1; runtime-claims=0");
    }
}
