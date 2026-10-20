using System.Collections.Immutable;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing.Patterns;

namespace Hoard.Hosting.Routing;

public sealed class HoardOwnedRoute
{
    private HoardOwnedRoute(string owner, string responsibility, RoutePattern pattern,
        ImmutableArray<string> methods, RequestDelegate handler)
    {
        ModuleId = owner;
        ResponsibilityId = responsibility;
        Pattern = pattern;
        Methods = methods;
        Handler = handler;
    }

    public string ModuleId { get; }
    public string ResponsibilityId { get; }
    public ImmutableArray<string> Methods { get; }
    public decimal Precedence => Pattern.InboundPrecedence;
    public int Order => 0;
    internal RoutePattern Pattern { get; }
    internal RequestDelegate Handler { get; }

    internal static HoardOwnedRoute? Create(string owner, string responsibility, string pattern,
        IEnumerable<string> methods, RequestDelegate handler)
    {
        if (pattern.Length > 2048 || !pattern.StartsWith('/') || pattern.Contains("//", StringComparison.Ordinal))
        { return null; }
        var list = methods.Take(10).ToImmutableArray();
        string[] supported = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"];
        if (list.IsEmpty || list.Any(method => !supported.Contains(method, StringComparer.Ordinal))
            || list.Distinct(StringComparer.Ordinal).Count() != list.Length) { return null; }
        RoutePattern parsed;
        try { parsed = RoutePatternFactory.Parse(pattern); }
        catch (RoutePatternException) { return null; }
        if (!Supported(parsed)) { return null; }
        return new(owner, responsibility, parsed, list, handler);
    }

    internal static bool Supported(RoutePattern pattern) => pattern.Parameters.Select(p => p.Name).Distinct(StringComparer.OrdinalIgnoreCase).Count()
        == pattern.Parameters.Count && pattern.PathSegments.All(segment => segment.Parts.Count == 1
            && (segment.Parts[0] is RoutePatternLiteralPart || segment.Parts[0] is RoutePatternParameterPart
            { IsOptional: false, IsCatchAll: false, Default: null, ParameterPolicies.Count: 0 }));
}
