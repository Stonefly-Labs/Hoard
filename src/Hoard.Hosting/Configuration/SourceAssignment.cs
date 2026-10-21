using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

internal sealed class SourceAssignment(string identity, object value, HoardConfigurationSource source)
{
    internal string Identity { get; } = identity;
    internal object Value { get; } = value;
    internal HoardConfigurationSource Source { get; } = source;
    public override string ToString() => "Private configuration assignment";
}

internal sealed class SecretReference(string kind, string target)
{
    internal string Kind { get; } = kind;
    internal string Target { get; } = target;
    public override string ToString() => "Private secret reference";
}

internal sealed class EffectiveConfiguration(IEnumerable<SourceAssignment> assignments)
{
    internal ImmutableDictionary<string, SourceAssignment> Assignments { get; } =
        assignments.ToImmutableDictionary(item => item.Identity, StringComparer.Ordinal);
    internal T Get<T>(string identity) => Assignments.TryGetValue(identity, out var assignment) && assignment.Value is T value
        ? value : throw new ConfigurationFailure(HoardConfigurationRule.InvalidSelection);
    internal bool TryGet(string identity, out object? value)
    {
        if (Assignments.TryGetValue(identity, out var assignment)) { value = assignment.Value; return true; }
        value = null;
        return false;
    }
    internal ImmutableArray<HoardSettingProvenance> Provenance => Assignments.Values.OrderBy(item => item.Identity, StringComparer.Ordinal)
        .Select(item => new HoardSettingProvenance(item.Identity, item.Source)).ToImmutableArray();
    public override string ToString() => "Private effective configuration";
}
