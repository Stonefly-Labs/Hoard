using System.Diagnostics.CodeAnalysis;
using System.Text.RegularExpressions;
using NuGet.Versioning;

namespace Hoard.Foundation.Tests;

internal static class CompatibilityExampleEvaluator
{
    private const string VersionPattern = @"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?";

    private static bool Version(string text, [NotNullWhen(true)] out NuGetVersion? version)
    {
        version = null;
        return Regex.IsMatch(text, $"^{VersionPattern}$", RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))
            && NuGetVersion.TryParse(text, out version);
    }

    private static VersionRange? Range(string? text)
    {
        if (text is null || !Regex.IsMatch(text,
            $@"^(?:\[{VersionPattern}\]|[\[(]{VersionPattern},\s*{VersionPattern}[\])])$",
            RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))
            || !VersionRange.TryParse(text, out var range) || range.MinVersion is null || range.MaxVersion is null)
        {
            return null;
        }
        var comparison = VersionComparer.VersionRelease.Compare(range.MinVersion, range.MaxVersion);
        return comparison > 0 || (comparison == 0 && !(range.IsMinInclusive && range.IsMaxInclusive)) ? null : range;
    }

    internal static bool Axis(string? range, string candidate, bool allowPrerelease) =>
        Range(range) is { } interval && Version(candidate, out var version)
        && (allowPrerelease || !version.IsPrerelease) && interval.Satisfies(version);

    internal static bool Platform(string module, string? hostRange, string host, bool allowHost,
        string? abstractionsRange, string abstractions, bool allowAbstractions) =>
        Version(module, out _) && Axis(hostRange, host, allowHost) && Axis(abstractionsRange, abstractions, allowAbstractions);

    internal sealed record DependencyResult(bool Supported, bool IntegrationAvailable, string Selection, string Reason);

    internal static DependencyResult Dependency(bool optional, string selection, string? range, string candidate, bool allowPrerelease)
    {
        if (selection is not ("absent" or "installed-disabled" or "registered-disabled" or "enabled"))
        {
            throw new ArgumentOutOfRangeException(nameof(selection));
        }
        if (Range(range) is null)
        {
            return new(false, false, selection, "Unsupported declaration: missing or disallowed dependency interval.");
        }
        if (selection != "enabled")
        {
            return new(optional, false, selection, optional
                ? "Optional target unavailable: no integration, capability claim, or active dependency edge."
                : "Required target unavailable: explicit operator correction required.");
        }
        var supported = Axis(range, candidate, allowPrerelease);
        return new(supported, supported, selection, supported
            ? "Enabled dependency meets its range and prerelease flag; platform axes still require qualification."
            : "Unsupported selected composition: do not disable, ignore, or substitute the incompatible target.");
    }
}
