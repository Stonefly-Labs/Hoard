using System.Text.Json;
using System.Text.RegularExpressions;

namespace Hoard.Conformance.TestLogger;

internal static class RuntimeVersionOutput
{
    private const string Prefix = "Hoard.Composition.Tests.ConformanceVersionTests.";

    internal static bool TryRead(string line, RuntimeExpectedTest expected, out JsonElement observation)
    {
        observation = default;
        if (!expected.FullyQualifiedName.StartsWith(Prefix, StringComparison.Ordinal)) { return false; }
        var method = expected.FullyQualifiedName[Prefix.Length..];
        string pattern;
        string kind;
        string[] names;
        switch (method)
        {
            case "Runtime_matrix":
                var axis = Argument(expected, "axis", "(?:host|abstractions|required|optional)");
                var row = Argument(expected, "row", "[a-z][a-z-]{0,40}");
                if (axis is null || row is null) { return false; }
                var stem = "version/" + axis + "/" + row;
                var repair = line.StartsWith(stem + "/repair:", StringComparison.Ordinal);
                kind = repair ? "repair" : "runtime";
                pattern = Regex.Escape(stem + (repair ? "/repair" : ""))
                    + @": accepted=([01]); constructors=(0); diagnostics=([0-9]{1,3})"
                    + (repair ? @"; active-edges=([01])" : "");
                names = repair ? ["accepted", "constructors", "diagnostics", "activeEdges"]
                    : ["accepted", "constructors", "diagnostics"];
                break;
            case "Platform_prerelease_flags_are_independent":
                var host = BooleanArgument(expected, "host");
                var abstractions = BooleanArgument(expected, "abstractions");
                if (host is null || abstractions is null) { return false; }
                kind = "platform-flags";
                pattern = Regex.Escape("version/platform-flags/" + host + "/" + abstractions)
                    + @": accepted=([01]); constructors=(0)";
                names = ["accepted", "constructors"];
                break;
            case "Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability":
                var selection = Argument(expected, "selection", "(?:absent|registered-disabled)");
                if (selection is null) { return false; }
                kind = "optional";
                pattern = Regex.Escape("version/optional/" + selection)
                    + @": active-edges=(0); capabilities=(0); demanded-capability-rejections=(1)";
                names = ["activeEdges", "capabilities", "capabilityRejections"];
                break;
            case "Inherited_runtime_classification":
                var id = Argument(expected, "id", "C-(?:0[1-9]|1[0-9]|2[0-3])(?:-outside)?");
                if (id is null) { return false; }
                kind = "classification";
                pattern = Regex.Escape("classification/" + id) + @": accepted=([01]); diagnostics=([0-9]{1,3})";
                names = ["accepted", "diagnostics"];
                break;
            case "Inherited_platform_flags_do_not_derive_from_module_version":
                var platformId = Argument(expected, "id", "C-(?:11|18)");
                if (platformId is null) { return false; }
                kind = "platform-classification";
                pattern = Regex.Escape("classification/" + platformId) + @": accepted=(0); unsupported-platform=([0-9]{1,3})";
                names = ["accepted", "unsupportedPlatform"];
                break;
            case "Inherited_release_classifier_is_policy_not_runtime_evidence":
                var policyId = Argument(expected, "id", "C-(?:05|06|16|17)");
                if (policyId is null) { return false; }
                kind = "policy";
                pattern = Regex.Escape("classification/" + policyId)
                    + @": policy-invalid=(1); repaired-policy-valid=(1); runtime-claims=(0)";
                names = ["policyInvalid", "policyRepaired", "runtimeClaims"];
                break;
            default: return false;
        }
        var match = Regex.Match(line, "\\A" + pattern + "\\z", RegexOptions.CultureInvariant,
            TimeSpan.FromMilliseconds(100));
        if (!match.Success) { return false; }
        var counters = names.Select((name, index) => (name, value: int.Parse(match.Groups[index + 1].Value,
            System.Globalization.CultureInfo.InvariantCulture))).ToDictionary(item => item.name, item => item.value);
        observation = JsonSerializer.SerializeToElement(new { kind, counters });
        return true;
    }

    internal static void Validate(IReadOnlyList<JsonElement> observations, RuntimeExpectedTest expected, bool passed)
    {
        var kinds = observations.Select(item => item.GetProperty("kind").GetString()).ToArray();
        RuntimeSafety.Require(kinds.Length <= 2 && kinds.Distinct(StringComparer.Ordinal).Count() == kinds.Length,
            "ProofMismatch");
        if (!passed || !expected.FullyQualifiedName.StartsWith(Prefix, StringComparison.Ordinal)) { return; }
        var required = expected.FullyQualifiedName[Prefix.Length..] switch
        {
            "Runtime_matrix" => "runtime",
            "Platform_prerelease_flags_are_independent" => "platform-flags",
            "Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability" => "optional",
            "Inherited_runtime_classification" => "classification",
            "Inherited_platform_flags_do_not_derive_from_module_version" => "platform-classification",
            "Inherited_release_classifier_is_policy_not_runtime_evidence" => "policy",
            _ => throw RuntimeSafety.Error("WitnessMissing")
        };
        RuntimeSafety.Require(kinds.Contains(required), "EvidenceIncomplete");
        if (required == "runtime")
        {
            var primary = observations.Single(item => item.GetProperty("kind").GetString() == "runtime");
            string[] stages = primary.GetProperty("counters").GetProperty("accepted").GetInt32() == 0
                ? ["repair", "runtime"] : ["runtime"];
            RuntimeSafety.Require(kinds.SequenceEqual(stages), "EvidenceIncomplete");
        }
    }

    private static string? Argument(RuntimeExpectedTest expected, string name, string values)
    {
        var match = Regex.Match(expected.TestIdentity, "(?:\\(|, )" + Regex.Escape(name)
            + ": \"(" + values + ")\"(?=,|\\))", RegexOptions.CultureInvariant, TimeSpan.FromMilliseconds(100));
        return match.Success ? match.Groups[1].Value : null;
    }

    private static string? BooleanArgument(RuntimeExpectedTest expected, string name)
    {
        var match = Regex.Match(expected.TestIdentity, "(?:\\(|, )" + Regex.Escape(name)
            + ": (True|False)(?=,|\\))", RegexOptions.CultureInvariant, TimeSpan.FromMilliseconds(100));
        return match.Success ? match.Groups[1].Value : null;
    }
}
