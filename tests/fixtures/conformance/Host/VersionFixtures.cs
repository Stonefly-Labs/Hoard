using Hoard.Abstractions.Modules;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Fixtures.Conformance.Host;

public static class VersionFixtures
{
    public sealed record Row(string Id, string Range, string Candidate, bool Prerelease, bool Accepted);
    public static IReadOnlyList<Row> Rows { get; } =
    [
        new("inclusive-lower", "[0.1.0,0.2.0)", "0.1.0", false, true),
        new("exclusive-upper", "[0.1.0,0.2.0)", "0.2.0", false, false),
        new("exclusive-lower", "(0.1.0,0.2.0]", "0.1.0", false, false),
        new("inclusive-upper", "(0.1.0,0.2.0]", "0.2.0", false, true),
        new("exact-build", "[0.1.0]", "0.1.0+build.7", false, true),
        new("rc-blocked", "[0.1.0,0.2.0)", "0.1.1-rc.1", false, false),
        new("rc-enabled", "[0.1.0,0.2.0)", "0.1.1-rc.1", true, true),
        new("below-stable-lower", "[0.1.1,0.2.0)", "0.1.1-rc.1", true, false),
        new("range-not-opt-in", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", false, false),
        new("rc-range-enabled", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", true, true),
        new("upper-rc-blocked", "[0.1.0,0.2.0)", "0.2.0-rc.1", false, false),
        new("upper-rc-enabled", "[0.1.0,0.2.0)", "0.2.0-rc.1", true, true),
        new("case-precedence", "[0.1.1-RC.1]", "0.1.1-rc.1", true, true),
        new("empty", "", "0.1.1", false, false),
        new("floating", "1.*", "0.1.1", false, false),
        new("unbounded", "[0.1.0,)", "0.1.1", false, false),
        new("reversed", "[0.2.0,0.1.0]", "0.1.1", false, false),
        new("empty-open", "(0.1.0,0.1.0)", "0.1.1", false, false),
        new("short-range", "[0.1]", "0.1.1", false, false),
        new("four-part-candidate", "[0.1.0,0.2.0)", "0.1.0.0", false, false),
        new("unsafe-candidate", "[0.1.0,0.2.0)", "credential=conformance-secret", false, false)
    ];

    public static Row Repair(string id)
    {
        var row = Rows.Single(item => item.Id == id);
        return id switch
        {
            "exclusive-upper" => row with { Candidate = "0.1.0", Accepted = true },
            "exclusive-lower" => row with { Candidate = "0.2.0", Accepted = true },
            "rc-blocked" or "range-not-opt-in" or "upper-rc-blocked" => row with { Prerelease = true, Accepted = true },
            "below-stable-lower" => row with { Candidate = "0.1.1", Accepted = true },
            "empty" or "floating" or "unbounded" or "reversed" or "empty-open" or "short-range" =>
                row with { Range = "[0.1.0,0.2.0)", Accepted = true },
            "four-part-candidate" or "unsafe-candidate" => row with { Candidate = "0.1.0", Accepted = true },
            _ => throw new ArgumentOutOfRangeException(nameof(id), "Only rejected rows require a repair.")
        };
    }

    public static (CompositionFixtures.Registry Registry, HoardCompositionValidation Result) Evaluate(
        string axis, string range, string candidate, bool prerelease, string selection = "enabled")
    {
        var registry = new CompositionFixtures.Registry();
        var versions = CompositionFixtures.Versions;
        var enabled = CompositionFixtures.Selection();
        if (axis is "host" or "abstractions")
        {
            foreach (var id in new[] { "metadata", "artifact" })
            {
                registry.Replace(id, declaration => declaration with
                {
                    Compatibility = declaration.Compatibility with
                    {
                        HostRange = axis == "host" ? range : "[0.1.0,0.2.0)",
                        AbstractionsRange = axis == "abstractions" ? range : "[0.1.0,0.2.0)",
                        AllowPrereleaseHost = axis == "host" && prerelease,
                        AllowPrereleaseAbstractions = axis == "abstractions" && prerelease
                    }
                });
            }
            versions = axis == "host" ? versions with { HostVersion = candidate }
                : versions with { AbstractionsVersion = candidate };
        }
        else
        {
            registry.Replace("metadata", declaration => declaration with
            { Dependencies = [CompositionFixtures.Dependency("protocol", axis == "optional", range, prerelease)] });
            if (selection != "absent")
            {
                registry.Protocol(CompositionFixtures.Declaration("protocol", ModuleCategory.Protocol) with
                {
                    Version = candidate,
                    Capabilities = [new() { Id = "integration", Version = "0.1.0", Description = "Enabled target only." }]
                });
            }
            if (selection == "enabled") { enabled = CompositionFixtures.Selection("protocol"); }
        }
        return (registry, registry.Builder.ValidateComposition(enabled, versions, new HoardLifecycleOptions()));
    }
}
