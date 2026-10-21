using System.Collections.Immutable;
using System.Globalization;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Configuration;

namespace Hoard.Hosting.Discovery;

internal static class DiscoveryOptionProjector
{
    internal static ImmutableArray<DiscoveryOption> Project(ModuleDescriptor descriptor,
        ImmutableArray<HoardOptionField> fields, DiscoveryPublicationPolicy? policy)
    {
        var options = ImmutableArray.CreateBuilder<DiscoveryOption>();
        foreach (var requirement in descriptor.Configuration.OrderBy(item => item.Key, StringComparer.Ordinal))
        {
            var field = fields.SingleOrDefault(item => item.Key == requirement.Key);
            var approved = policy?.Options.SingleOrDefault(item => item.Id == requirement.Key);
            var secret = requirement.SecretReference;
            if (field is not null && (!Enum.IsDefined(field.Type)
                || secret != (field.Type == HoardOptionType.Secret)
                || field.MinimumLength < 0 || field.MaximumLength < field.MinimumLength || field.MaximumLength > 16384
                || field.Minimum > field.Maximum))
            { throw new HoardDiscoverySetupException(); }
            if (secret && approved is not null && (approved.PublicDefault is not null || !approved.AllowedValues.IsEmpty))
            { throw new HoardDiscoverySetupException(); }
            options.Add(new(requirement.Key, secret ? "secret" : field?.Type.ToString().ToLowerInvariant() ?? "string",
                requirement.Required, secret, approved?.Description,
                field is null || secret ? null : new(field.MinimumLength, field.MaximumLength,
                    field.Minimum.ToString(CultureInfo.InvariantCulture), field.Maximum.ToString(CultureInfo.InvariantCulture)),
                secret ? null : approved?.PublicDefault,
                secret || approved is null || approved.AllowedValues.IsEmpty ? null : approved.AllowedValues));
        }
        return options.ToImmutable();
    }
}
