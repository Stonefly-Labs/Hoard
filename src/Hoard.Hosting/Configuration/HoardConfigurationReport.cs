using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

public enum HoardConfigurationSource { Defaults, File, Environment, CommandLine }
public enum HoardConfigurationPhase { Sources, Structure, Merge, Composition, PublicOptions, Secrets, SecretOptions, Conversion, Publication }
public enum HoardConfigurationOutcome { Validated, Failed, Cancelled, TimedOut }
public enum HoardConfigurationRule
{
    InvalidBudget, SourceUnavailable, InvalidSource, DuplicateSetting, UnknownSetting, InputLimit,
    UnsupportedVersion, InvalidSelection, CompositionRejected, MissingConfigurationContract,
    InvalidConfigurationContract, MissingConfigurationAdapter, MissingOption, InvalidOption,
    InvalidSecretReference, UnsupportedSecretKind, SecretUnavailable, InvalidCheckResult, CheckFailure,
    Cancelled, Timeout, CancellationFailure, LateCheckFailure, StaleConfiguration, ConfigurationRequired,
    ConversionRejected, PublicationFailed, IncompleteConfiguration
}

public sealed record HoardConfigurationDiagnostic
{
    internal HoardConfigurationDiagnostic(HoardConfigurationRule rule, HoardConfigurationPhase phase,
        HoardConfigurationSource source, string owner, string setting, Guid correlation)
    { Rule = rule; Phase = phase; Source = source; Owner = owner; Setting = setting; CorrelationId = correlation; }
    public HoardConfigurationRule Rule { get; }
    public HoardConfigurationPhase Phase { get; }
    public HoardConfigurationSource Source { get; }
    public string Owner { get; }
    public string Setting { get; }
    public Guid CorrelationId { get; }
    public string CorrectiveAction => Rule switch
    {
        HoardConfigurationRule.Timeout or HoardConfigurationRule.LateCheckFailure =>
            "Inspect trusted callback cooperation; terminate the process if pending inputs cannot be released.",
        HoardConfigurationRule.Cancelled => "Evaluate a fresh explicit configuration before starting.",
        HoardConfigurationRule.SecretUnavailable => "Provide a valid supported secret reference for the selected owner.",
        HoardConfigurationRule.StaleConfiguration => "Reevaluate the current builder and consume a fresh proof once.",
        HoardConfigurationRule.InvalidBudget => "Supply positive finite trusted configuration budgets and supported input limits.",
        _ => "Correct the named configuration rule and evaluate the complete configuration again."
    };
}

public sealed record HoardSettingProvenance(string Setting, HoardConfigurationSource Source);
public sealed record HoardConfigurationReport(Guid CorrelationId,
    ImmutableArray<HoardConfigurationDiagnostic> Diagnostics, int OmittedCount,
    ImmutableArray<HoardSettingProvenance> Provenance);
public sealed record HoardConfigurationSupervision(int PendingCount,
    ImmutableArray<HoardConfigurationDiagnostic> Diagnostics, int OmittedCount);

internal sealed class ConfigurationFailure(HoardConfigurationRule rule) : Exception("Hoard configuration rejected.")
{
    internal HoardConfigurationRule Rule { get; } = rule;
}
