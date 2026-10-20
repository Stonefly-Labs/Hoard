using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Composition;

internal static class RegistryValidator
{
    internal static bool Text(string? value, int limit = 2048) =>
        !string.IsNullOrWhiteSpace(value) && value.Length <= limit;

    private static bool Items<T>(ImmutableArray<T> items, Func<T, string> key, Func<T, bool> valid)
        where T : class => !items.IsDefault && items.Length <= 1000
        && items.All(item => item is not null && valid(item))
        && items.Select(key).Distinct(StringComparer.Ordinal).Count() == items.Length;

    private static bool PublicUrl(Uri? value) => value is null || (value.IsAbsoluteUri
        && value.OriginalString.Length <= 2048 && value.Scheme is "https" or "http"
        && string.IsNullOrEmpty(value.UserInfo) && string.IsNullOrEmpty(value.Query)
        && string.IsNullOrEmpty(value.Fragment) && !value.IsLoopback);

    internal static bool Descriptor(ModuleDescriptor? declaration)
    {
        if (declaration is null) { return false; }
        var compatibility = declaration.Compatibility;
        var provenance = declaration.Provenance;
        return HoardLifecycleDiagnostic.IsSafeId(declaration.Id) && Enum.IsDefined(declaration.Category)
            && RuntimeCompatibility.Version(declaration.Version, out _) && compatibility is not null
            && RuntimeCompatibility.Range(compatibility.HostRange) is not null
            && RuntimeCompatibility.Range(compatibility.AbstractionsRange) is not null
            && provenance is not null && Text(provenance.Publisher, 256) && Enum.IsDefined(provenance.SupportStatus)
            && PublicUrl(provenance.SourceUrl) && PublicUrl(provenance.SupportUrl)
            && Items(declaration.Dependencies, item => item.ModuleId, item =>
                HoardLifecycleDiagnostic.IsSafeId(item.ModuleId) && item.ModuleId != declaration.Id
                && RuntimeCompatibility.Range(item.VersionRange) is not null)
            && Items(declaration.Capabilities, item => item.Id, item =>
                HoardLifecycleDiagnostic.IsSafeId(item.Id) && RuntimeCompatibility.Version(item.Version, out _) && Text(item.Description))
            && Items(declaration.Configuration, item => item.Key, item => Text(item.Key, 256) && Text(item.Description))
            && Items(declaration.Endpoints, item => item.Id, item => HoardLifecycleDiagnostic.IsSafeId(item.Id) && Text(item.Description))
            && Items(declaration.Health, item => item.Id, item => HoardLifecycleDiagnostic.IsSafeId(item.Id) && Text(item.Description));
    }

    internal static bool Provider(Type? type, ModuleCategory category)
    {
        if (type is null || !type.IsClass || type.IsAbstract || type.ContainsGenericParameters) { return false; }
        Type[] families = [typeof(IProtocolProvider), typeof(IMetadataProvider), typeof(IArtifactProvider), typeof(IIdentityProvider)];
        return families.Count(family => family.IsAssignableFrom(type)) == 1
            && Enum.IsDefined(category) && families[(int)category].IsAssignableFrom(type);
    }

    internal static bool Adapter(Type? type) => type is not null && type.IsClass && !type.IsAbstract
        && !type.ContainsGenericParameters && typeof(IHoardModule).IsAssignableFrom(type)
        && type.GetConstructor(Type.EmptyTypes) is not null;
}
