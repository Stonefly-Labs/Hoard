using System.Collections.Immutable;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Configuration;

internal static class ConfigurationOptionChecker
{
    internal static async Task<ImmutableDictionary<string, HoardModuleOptions>> CheckAsync(
        HoardValidatedComposition composition, EffectiveConfiguration effective,
        ImmutableDictionary<string, ConfigurationRegistration> metadata, ConfigurationSupervisor supervisor)
    {
        var owners = ImmutableDictionary.CreateBuilder<string, HoardModuleOptions>(StringComparer.Ordinal);
        foreach (var id in composition.ActivationOrder)
        {
            var registration = metadata[id];
            var contract = registration.Contract;
            if (!contract.Fields.IsEmpty)
            {
                var versionSetting = $"modules:{id}:optionsversion";
                if (!effective.TryGet(versionSetting, out var version) || version is not 1L)
                {
                    var source = effective.Assignments.TryGetValue(versionSetting, out var assignment)
                        ? assignment.Source : HoardConfigurationSource.Defaults;
                    supervisor.Reject(HoardConfigurationRule.UnsupportedVersion, HoardConfigurationPhase.PublicOptions,
                        source, id, versionSetting);
                }
                var adapter = composition.Adapters.Single(a => a.ProviderType == registration.ProviderType);
                if (!typeof(IHoardConfiguredModule).IsAssignableFrom(adapter.ModuleType))
                { supervisor.Reject(HoardConfigurationRule.MissingConfigurationAdapter, HoardConfigurationPhase.PublicOptions, owner: id); }
            }
            var values = new Dictionary<string, object>(StringComparer.Ordinal);
            foreach (var field in contract.Fields)
            {
                supervisor.Check();
                var key = ConfigurationNames.Canonical(field.Key)!;
                var setting = $"modules:{id}:options:{key}";
                if (!effective.TryGet(setting, out var value))
                {
                    if (field.Required)
                    { supervisor.Reject(HoardConfigurationRule.MissingOption, HoardConfigurationPhase.PublicOptions, owner: id, setting: setting); }
                    continue;
                }
                if (field.Type == HoardOptionType.Secret) { continue; }
                var valid = value switch
                {
                    string text => text.Length >= field.MinimumLength && text.Length <= field.MaximumLength
                        && (field.AllowedValues.IsEmpty || field.AllowedValues.Contains(text, StringComparer.Ordinal))
                        && (field.Type != HoardOptionType.Address || Uri.TryCreate(text, UriKind.Absolute, out var uri)
                            && uri.Scheme is "http" or "https" && uri.Host.Length != 0
                            && uri.UserInfo.Length == 0 && uri.Query.Length == 0 && uri.Fragment.Length == 0),
                    long number => number >= field.Minimum && number <= field.Maximum,
                    bool => true,
                    _ => false
                };
                if (!valid)
                {
                    supervisor.Reject(HoardConfigurationRule.InvalidOption, HoardConfigurationPhase.PublicOptions,
                    effective.Assignments[setting].Source, id, setting);
                }
                values.Add(key, value!);
            }
            var ownerOptions = new HoardModuleOptions(values);
            supervisor.Hold(new OwnerOptionsLease(ownerOptions));
            owners.Add(id, ownerOptions);
            await ValidateAsync(id, registration, ownerOptions, effective, HoardOptionCheckPhase.Public, supervisor).ConfigureAwait(false);
        }
        return owners.ToImmutable();
    }

    internal static async Task ValidateAsync(string id, ConfigurationRegistration registration, HoardModuleOptions options,
        EffectiveConfiguration effective, HoardOptionCheckPhase phase, ConfigurationSupervisor supervisor)
    {
        if (registration.Validator is not { } validator) { return; }
        var at = phase == HoardOptionCheckPhase.Public ? HoardConfigurationPhase.PublicOptions : HoardConfigurationPhase.SecretOptions;
        var references = registration.Contract.Fields.Where(f => f.Type == HoardOptionType.Secret)
            .Select(f => ConfigurationNames.Canonical(f.Key)!)
            .Where(key => effective.TryGet($"modules:{id}:options:{key}", out _));
        var context = new HoardOptionCheckContext(phase, options, references);
        var result = await supervisor.RunAsync(at, HoardConfigurationSource.Defaults, id,
            token => validator(context, token)).ConfigureAwait(false);
        if (result is null || result.Violations.IsDefault || result.Violations.Length > 256
            || result.Violations.Any(v => v is null || !registration.Contract.Fields.Any(f => ConfigurationNames.Canonical(f.Key) == v.Field)
                || !registration.Contract.RuleIds.Contains(v.Rule, StringComparer.Ordinal)))
        { supervisor.Reject(HoardConfigurationRule.InvalidCheckResult, at, owner: id); }
        foreach (var violation in result.Violations)
        {
            var setting = $"modules:{id}:options:{violation.Field}";
            var source = effective.Assignments.TryGetValue(setting, out var assignment)
                ? assignment.Source : HoardConfigurationSource.Defaults;
            supervisor.Reject(HoardConfigurationRule.CheckFailure, at, source, id, setting, violation.Rule);
        }
    }
}
