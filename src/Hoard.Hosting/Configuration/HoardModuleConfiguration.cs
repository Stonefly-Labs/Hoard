using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

public sealed class HoardModuleConfiguration
{
    public HoardModuleConfiguration(int optionsVersion, IEnumerable<HoardOptionField> fields,
        IEnumerable<string>? ruleIds = null)
    {
        ArgumentNullException.ThrowIfNull(fields);
        OptionsVersion = optionsVersion;
        Fields = fields.Take(257).ToImmutableArray();
        RuleIds = (ruleIds ?? []).Take(257).ToImmutableArray();
    }

    public int OptionsVersion { get; }
    public ImmutableArray<HoardOptionField> Fields { get; }
    public ImmutableArray<string> RuleIds { get; }
    public override string ToString() => "Hoard module configuration metadata";
}
