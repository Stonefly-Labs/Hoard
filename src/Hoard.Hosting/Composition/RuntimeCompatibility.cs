using System.Diagnostics.CodeAnalysis;
using System.Text.RegularExpressions;
using NuGet.Versioning;

namespace Hoard.Hosting.Composition;

internal static class RuntimeCompatibility
{
    private const string VersionPattern = @"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?";

    internal static bool Version(string? text, [NotNullWhen(true)] out NuGetVersion? version)
    {
        version = null;
        return text is { Length: > 0 and <= 256 }
            && Regex.IsMatch(text, $@"\A{VersionPattern}\z", RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))
            && NuGetVersion.TryParse(text, out version);
    }

    internal static VersionRange? Range(string? text)
    {
        if (text is not { Length: > 0 and <= 512 } || !Regex.IsMatch(text,
            $@"\A(?:\[{VersionPattern}\]|[\[(]{VersionPattern},\s*{VersionPattern}[\])])\z",
            RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))
            || !VersionRange.TryParse(text, out var range) || range.MinVersion is null || range.MaxVersion is null)
        {
            return null;
        }
        var comparison = VersionComparer.VersionRelease.Compare(range.MinVersion, range.MaxVersion);
        return comparison > 0 || (comparison == 0 && !(range.IsMinInclusive && range.IsMaxInclusive)) ? null : range;
    }

    internal static bool Axis(string? range, string? candidate, bool allowPrerelease) =>
        Range(range) is { } interval && Version(candidate, out var version)
        && (allowPrerelease || !version.IsPrerelease) && interval.Satisfies(version);
}
