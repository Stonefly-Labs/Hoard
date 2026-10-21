using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

public enum HoardOptionType { String, Boolean, Integer, Address, Secret }

public sealed record HoardOptionField
{
    public HoardOptionField(string key, HoardOptionType type, bool required = false)
    { Key = key; Type = type; Required = required; }

    public string Key { get; init; }
    public HoardOptionType Type { get; init; }
    public bool Required { get; init; }
    public int MinimumLength { get; init; }
    public int MaximumLength { get; init; } = 16 * 1024;
    public long Minimum { get; init; } = long.MinValue;
    public long Maximum { get; init; } = long.MaxValue;
    public ImmutableArray<string> AllowedValues { get; init; } = [];
    public string? Example { get; init; }
    public string? DocumentedDefault { get; init; }
}
