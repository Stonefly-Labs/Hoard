using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

internal static class ConfigurationMetadata
{
    internal static ImmutableDictionary<string, ConfigurationRegistration> Validate(HoardBuilder builder,
        HoardConfigurationOptions limits, ConfigurationSupervisor supervisor)
    {
        supervisor.Known("configuration",
            ["configurationversion", "enabledmodules", "metadatamodule", "artifactmodule", "identitymodules", "requiredcapabilities", "modules"]);
        var registrations = builder.Services.Where(item => item.ServiceType == typeof(HoardModuleRegistration))
            .Select(item => item.ImplementationInstance as HoardModuleRegistration).ToArray();
        var associations = builder.Services.Where(item => item.ServiceType == typeof(ConfigurationRegistration))
            .Select(item => item.ImplementationInstance as ConfigurationRegistration).ToArray();
        var result = ImmutableDictionary.CreateBuilder<string, ConfigurationRegistration>(StringComparer.Ordinal);
        foreach (var association in associations)
        {
            supervisor.Check();
            if (association is null || registrations.Count(item => item?.ProviderType == association.ProviderType) != 1
                || associations.Count(item => item?.ProviderType == association.ProviderType) != 1)
            { supervisor.Reject(HoardConfigurationRule.InvalidConfigurationContract, HoardConfigurationPhase.Composition); }
        }
        foreach (var registration in registrations)
        {
            supervisor.Check();
            if (registration is null || registration.Declaration is null || registration.Declaration.Configuration.IsDefault
                || ConfigurationNames.Canonical(registration.Declaration.Id) != registration.Declaration.Id)
            { supervisor.Reject(HoardConfigurationRule.InvalidConfigurationContract, HoardConfigurationPhase.Composition); }
            var declaration = registration!.Declaration;
            var association = associations.SingleOrDefault(item => item!.ProviderType == registration.ProviderType);
            if (association is null)
            {
                if (!declaration.Configuration.IsEmpty)
                { supervisor.Reject(HoardConfigurationRule.MissingConfigurationContract, HoardConfigurationPhase.Composition); }
                association = new(registration.ProviderType, new(1, []), null);
            }
            var contract = association.Contract;
            if (contract is null || contract.OptionsVersion != 1 || contract.Fields.Length > limits.MaximumFieldsPerModule
                || contract.RuleIds.Length > limits.MaximumFieldsPerModule
                || contract.RuleIds.Any(id => ConfigurationNames.Canonical(id) != id)
                || contract.RuleIds.Distinct(StringComparer.Ordinal).Count() != contract.RuleIds.Length
                || contract.Fields.Any(field => field is null || ConfigurationNames.Canonical(field.Key) is null
                    || !Enum.IsDefined(field.Type) || field.MinimumLength < 0 || field.MaximumLength < field.MinimumLength
                    || field.MaximumLength > 16 * 1024 || field.Minimum > field.Maximum
                    || field.AllowedValues.IsDefault || field.AllowedValues.Length > limits.MaximumFieldsPerModule
                    || field.AllowedValues.Any(value => value is null || value.Length > limits.MaximumStringBytes)
                    || field.Type == HoardOptionType.Secret && (field.DocumentedDefault is not null || field.Example is not null
                        || !field.AllowedValues.IsEmpty))
                || contract.Fields.Select(field => ConfigurationNames.Canonical(field.Key)).Distinct(StringComparer.Ordinal).Count()
                    != contract.Fields.Length
                || declaration.Configuration.Length != contract.Fields.Length)
            { supervisor.Reject(HoardConfigurationRule.InvalidConfigurationContract, HoardConfigurationPhase.Composition); }
            foreach (var field in contract.Fields)
            {
                var key = ConfigurationNames.Canonical(field.Key);
                var requirements = declaration.Configuration.Where(item => item is not null
                    && ConfigurationNames.Canonical(item.Key) == key).ToArray();
                if (requirements.Length != 1 || requirements[0].Required != field.Required
                    || requirements[0].SecretReference != (field.Type == HoardOptionType.Secret))
                { supervisor.Reject(HoardConfigurationRule.InvalidConfigurationContract, HoardConfigurationPhase.Composition); }
            }
            if (result.ContainsKey(declaration.Id))
            { supervisor.Reject(HoardConfigurationRule.InvalidConfigurationContract, HoardConfigurationPhase.Composition); }
            result.Add(declaration.Id, association);
            supervisor.Known(declaration.Id, contract.Fields.Select(field => $"modules:{declaration.Id}:options:{ConfigurationNames.Canonical(field.Key)}")
                .Concat([$"modules:{declaration.Id}:optionsversion", $"modules:{declaration.Id}:options"]), contract.RuleIds);
        }
        return result.ToImmutable();
    }
}
