using System.Collections.Immutable;
using System.Text;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Configuration;

internal static class ConfigurationSecretResolver
{
    internal static async Task<ImmutableDictionary<string, HoardModuleOptions>> ResolveAsync(
        HoardConfigurationInput input, HoardValidatedComposition composition, EffectiveConfiguration effective,
        ImmutableDictionary<string, ConfigurationRegistration> metadata,
        ImmutableDictionary<string, HoardModuleOptions> ordinary, HoardConfigurationOptions limits,
        ConfigurationSupervisor supervisor)
    {
        var owners = ordinary.ToBuilder();
        foreach (var id in composition.ActivationOrder)
        {
            var values = ordinary[id].Values.ToBuilder();
            foreach (var field in metadata[id].Contract.Fields.Where(f => f.Type == HoardOptionType.Secret))
            {
                var key = ConfigurationNames.Canonical(field.Key)!;
                var setting = $"modules:{id}:options:{key}";
                if (!effective.TryGet(setting, out var value)) { continue; }
                var reference = (SecretReference)value!;
                var text = await supervisor.RunAsync(HoardConfigurationPhase.Secrets,
                    effective.Assignments[setting].Source, id, async token =>
                    {
                        try
                        {
                            string? secret;
                            if (reference.Kind == "env")
                            {
                                if (input.ReadEnvironment is { } reader)
                                { secret = await reader(reference.Target, token).ConfigureAwait(false); }
                                else if (OperatingSystem.IsWindows())
                                {
                                    var matches = input.Environment.Where(pair =>
                                        pair.Key.Equals(reference.Target, StringComparison.OrdinalIgnoreCase)).Take(2).ToArray();
                                    if (matches.Length != 1) { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                                    secret = matches[0].Value;
                                }
                                else { input.Environment.TryGetValue(reference.Target, out secret); }
                            }
                            else
                            {
                                if (input.ReadFile is { } reader)
                                { secret = await reader(reference.Target, token).ConfigureAwait(false); }
                                else
                                {
                                    var file = new FileInfo(reference.Target);
                                    if (file.LinkTarget is not null)
                                    {
                                        file = file.ResolveLinkTarget(true) as FileInfo
                                        ?? throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable);
                                    }
                                    if ((file.Attributes & (FileAttributes.Directory | FileAttributes.Device)) != 0
                                        || file.Length <= 0 || file.Length > limits.MaximumSecretBytes)
                                    { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                                    secret = await ConfigurationSourceResolution.ReadFileAsync(
                                        file.FullName, limits.MaximumSecretBytes, token).ConfigureAwait(false);
                                }
                            }
                            if (secret is null || secret.Length > limits.MaximumSecretBytes
                                || new UTF8Encoding(false, true).GetByteCount(secret) > limits.MaximumSecretBytes
                                || secret.Contains('\0'))
                            { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                            if (reference.Kind == "file")
                            {
                                if (secret.StartsWith('\uFEFF')) { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                                if (secret.EndsWith('\n'))
                                {
                                    secret = secret[..^1];
                                    if (secret.EndsWith('\r')) { secret = secret[..^1]; }
                                }
                            }
                            if (string.IsNullOrWhiteSpace(secret)) { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                            return secret;
                        }
                        catch (OperationCanceledException) { throw; }
                        catch (Exception) { throw new ConfigurationFailure(HoardConfigurationRule.SecretUnavailable); }
                    }).ConfigureAwait(false);
                var secretValue = new HoardSecretValue(text);
                var secretOptions = new HoardModuleOptions(new Dictionary<string, object> { [key] = secretValue });
                supervisor.Hold(new OwnerOptionsLease(secretOptions));
                values.Add(key, secretValue);
            }
            owners[id] = new HoardModuleOptions(values);
        }
        foreach (var id in composition.ActivationOrder)
        {
            await ConfigurationOptionChecker.ValidateAsync(id, metadata[id], owners[id], effective,
                HoardOptionCheckPhase.Secrets, supervisor).ConfigureAwait(false);
        }
        return owners.ToImmutable();
    }
}
