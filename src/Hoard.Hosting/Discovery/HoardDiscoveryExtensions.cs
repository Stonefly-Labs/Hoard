using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Hoard.Hosting.Discovery;

public static class HoardDiscoveryExtensions
{
    public static HoardBuilder AddHoardDiscovery(this HoardBuilder builder,
        HoardDiscoveryCatalog catalog, HoardDiscoveryOptions options)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(catalog);
        ArgumentNullException.ThrowIfNull(options);
        lock (builder.ConfigurationGate)
        {
            if (builder.DiscoveryFrozen || builder.DiscoveryRegistration is not null || builder.ConfigurationConsumed)
            { throw new HoardDiscoverySetupException(); }
            DiscoveryMetadata.Validate(catalog, options);
            builder.DiscoveryRegistration = new(catalog, options);
            builder.Services.AddSingleton(options);
            builder.Services.TryAddSingleton<IDiscoveryExposureAdapter, KestrelDiscoveryExposureAdapter>();
            builder.Services.TryAddEnumerable(ServiceDescriptor.Singleton<IAuthorizationHandler, DiscoveryExposureHandler>());
            builder.Services.AddSingleton<IHoardDiscoverySource>(_ =>
                builder.DiscoverySource ?? throw new HoardDiscoverySetupException());
        }
        return builder;
    }

    internal static void Freeze(HoardBuilder builder)
    {
        lock (builder.ConfigurationGate)
        {
            builder.DiscoveryFrozen = true;
            if (builder.DiscoveryRegistration is not { } registration) { return; }
            var metadata = builder.Services.Where(item => item.ServiceType == typeof(HoardModuleRegistration)
                || item.ServiceType == typeof(ConfigurationRegistration)).ToImmutableArray();
            if (registration.Frozen is not null)
            {
                if (!metadata.SequenceEqual(registration.MetadataSnapshot)) { throw new HoardDiscoverySetupException(); }
                return;
            }
            registration.Frozen = DiscoveryMetadata.Freeze(builder, registration.Catalog);
            registration.MetadataSnapshot = metadata;
        }
    }
}

internal sealed class DiscoveryRegistration(HoardDiscoveryCatalog catalog, HoardDiscoveryOptions options)
{
    internal HoardDiscoveryCatalog Catalog { get; } = catalog;
    internal HoardDiscoveryOptions Options { get; } = options;
    internal FrozenDiscovery? Frozen { get; set; }
    internal ImmutableArray<ServiceDescriptor> MetadataSnapshot { get; set; } = [];
}

internal sealed record FrozenDiscovery(ImmutableArray<DiscoveryModule> Modules,
    ImmutableArray<DiscoveryContribution> Contributions, ImmutableArray<DiscoveryServiceBinding> Services);

internal static class DiscoveryMetadata
{
    internal static bool Id(string? value) => HoardLifecycleDiagnostic.IsSafeId(value);
    private static bool Text(string? value, int limit) => value is null || value.Length <= limit
        && !value.Any(character => char.IsControl(character) || character is '<' or '>');
    private static void Require([DoesNotReturnIf(false)] bool valid)
    { if (!valid) { throw new HoardDiscoverySetupException(); } }
    private static bool Bounded<T>(ImmutableArray<T> array, int limit) => !array.IsDefault && array.Length <= limit;
    private static bool Unique<T>(IEnumerable<T> items) => items.Distinct().Count() == items.Count();
    private static bool Version(string value) => value is { Length: <= 128 } && RuntimeCompatibility.Version(value, out _);
    private static string Key(DiscoveryContribution item) =>
        $"{item.CapabilityId}/{item.Version}/{item.OperationId}/{string.Join(",", item.Owners.Order(StringComparer.Ordinal))}";

    internal static void Validate(HoardDiscoveryCatalog catalog, HoardDiscoveryOptions options)
    {
        Require(Id(catalog.DistributionId) && Version(catalog.DistributionVersion)
            && catalog.InventoryCompleteness is "complete" or "partial"
            && options.TimeProvider is not null && options.Deadline > TimeSpan.Zero
            && options.MaximumResponseBytes is > 0 and <= 4 * 1024 * 1024
            && Enum.IsDefined(options.Exposure) && options.ManagementReadPolicy is { Length: > 0 and <= 128 });
        Require(Bounded(catalog.IncludedModules, 256) && Bounded(catalog.Publications, 256)
            && Bounded(catalog.Contributions, 4096) && Bounded(catalog.ServiceBindings, 4096));
        foreach (var descriptor in catalog.IncludedModules) { ValidateDescriptor(descriptor); }
        Require(Unique(catalog.IncludedModules.Select(item => item.Id))
            && catalog.Publications.All(item => item is not null && Id(item.ModuleId))
            && Unique(catalog.Publications.Select(item => item.ModuleId)));
        foreach (var policy in catalog.Publications)
        {
            Require(Text(policy.Publisher, 160) && Bounded(policy.Options, 256));
            foreach (var option in policy.Options)
            {
                Require(option is not null && Id(option.Id) && Text(option.Description, 512)
                    && Text(option.PublicDefault, 512) && Bounded(option.AllowedValues, 64));
                Require(option!.AllowedValues.All(value => value is not null && Text(value, 160)));
            }
            Require(Unique(policy.Options.Select(item => item.Id)));
        }
        foreach (var contribution in catalog.Contributions)
        {
            Require(contribution is not null && Id(contribution.CapabilityId) && Version(contribution.Version)
                && Id(contribution.OperationId) && Bounded(contribution.Owners, 32) && !contribution.Owners.IsEmpty
                && Bounded(contribution.Dependencies, 32) && Bounded(contribution.Routes, 32)
                && Bounded(contribution.Services, 32) && Bounded(contribution.EvidenceIds, 32)
                && contribution.Routes.Length + contribution.Services.Length <= 32
                && contribution.Support is "supported" or "unsupported" or "unverified"
                && contribution.EvidenceScope is "fixture" or "production" or "unknown");
            Require(contribution!.Owners.All(Id) && Unique(contribution.Owners)
                && contribution.Dependencies.All(Id) && Unique(contribution.Dependencies)
                && contribution.Services.All(Id) && Unique(contribution.Services)
                && contribution.EvidenceIds.All(Id) && Unique(contribution.EvidenceIds)
                && contribution.Routes.All(route => route is not null && Id(route.OwnerId) && Id(route.ResponsibilityId)
                    && route.Method is "GET" or "HEAD" or "POST" or "PUT" or "PATCH" or "DELETE" or "OPTIONS")
                && Unique(contribution.Routes));
            Require(contribution.Support != "supported"
                || contribution.EvidenceScope != "unknown" && !contribution.EvidenceIds.IsEmpty);
        }
        Require(Unique(catalog.Contributions.Select(Key))
            && catalog.Contributions.GroupBy(item => item.Owners.Order(StringComparer.Ordinal).First())
                .All(group => group.Count() <= 64));
        Require(catalog.ServiceBindings.All(item => item is not null && Id(item.Id) && Id(item.OwnerId)
            && item.ServiceType is not null && !item.ServiceType.ContainsGenericParameters)
            && Unique(catalog.ServiceBindings.Select(item => item.Id)));
    }

    private static void ValidateDescriptor(ModuleDescriptor descriptor)
    {
        Require(descriptor is not null && Bounded(descriptor.Capabilities, 64)
            && Bounded(descriptor.Configuration, 256) && Bounded(descriptor.Dependencies, 32)
            && Bounded(descriptor.Endpoints, 32) && Bounded(descriptor.Health, 100));
        Require(RegistryValidator.Descriptor(descriptor) && Version(descriptor.Version)
            && descriptor.Compatibility.HostRange.Length <= 128
            && descriptor.Compatibility.AbstractionsRange.Length <= 128
            && descriptor.Configuration.All(field => Id(field.Key))
            && descriptor.Capabilities.All(capability => Version(capability.Version)));
    }

    internal static FrozenDiscovery Freeze(HoardBuilder builder, HoardDiscoveryCatalog catalog)
    {
        // Count before materialization: registration services are explicit host inputs, not a lazy catalog.
        Require(builder.Services.Count(item => item.ServiceType == typeof(HoardModuleRegistration)) <= 256);
        var registrations = builder.Services.Where(item => item.ServiceType == typeof(HoardModuleRegistration))
            .Select(item => item.ImplementationInstance as HoardModuleRegistration).ToArray();
        Require(registrations.All(item => item is not null));
        foreach (var registration in registrations) { ValidateDescriptor(registration!.Declaration); }
        Require(Unique(registrations.Select(item => item!.Declaration.Id)));
        var declarations = catalog.IncludedModules.ToDictionary(item => item.Id, StringComparer.Ordinal);
        foreach (var registration in registrations)
        {
            var descriptor = registration!.Declaration;
            if (declarations.TryGetValue(descriptor.Id, out var included))
            { Require(included.Category == descriptor.Category && included.Version == descriptor.Version); }
            declarations[descriptor.Id] = descriptor;
        }
        Require(declarations.Count <= 256
            && declarations.Values.Sum(item => item.Configuration.Length) <= 4096
            && declarations.Values.Sum(item => item.Capabilities.Length) <= 4096);
        Require(catalog.Publications.All(policy => declarations.ContainsKey(policy.ModuleId))
            && catalog.ServiceBindings.All(binding => declarations.ContainsKey(binding.OwnerId)));
        var contributions = catalog.Contributions.Select(item => item with
        {
            Owners = item.Owners.Order(StringComparer.Ordinal).ToImmutableArray(),
            Dependencies = item.Dependencies.Order(StringComparer.Ordinal).ToImmutableArray(),
            EvidenceIds = item.EvidenceIds.Order(StringComparer.Ordinal).ToImmutableArray()
        }).ToList();
        foreach (var contribution in contributions)
        {
            Require(contribution.Owners.All(owner => declarations.ContainsKey(owner)
                    && declarations[owner].Capabilities.Any(capability =>
                        capability.Id == contribution.CapabilityId && capability.Version == contribution.Version))
                && contribution.Routes.All(binding => contribution.Owners.Contains(binding.OwnerId)
                    && declarations[binding.OwnerId].Endpoints.Any(endpoint => endpoint.Id == binding.ResponsibilityId))
                && contribution.Services.All(id => catalog.ServiceBindings.Any(binding =>
                    binding.Id == id && contribution.Owners.Contains(binding.OwnerId))));
        }
        foreach (var descriptor in declarations.Values)
        {
            foreach (var capability in descriptor.Capabilities)
            {
                if (!contributions.Any(item => item.Owners.Contains(descriptor.Id)
                    && item.CapabilityId == capability.Id && item.Version == capability.Version))
                { contributions.Add(new(capability.Id, capability.Version, capability.Id, [descriptor.Id])); }
            }
        }
        Require(contributions.Count <= 4096 && contributions.GroupBy(item => item.Owners[0]).All(group => group.Count() <= 64));
        var modules = ImmutableArray.CreateBuilder<DiscoveryModule>();
        foreach (var descriptor in declarations.Values.OrderBy(item => item.Id, StringComparer.Ordinal))
        {
            var registration = registrations.SingleOrDefault(item => item!.Declaration.Id == descriptor.Id);
            var policy = catalog.Publications.SingleOrDefault(item => item.ModuleId == descriptor.Id);
            var contracts = builder.Services.Where(item => item.ServiceType == typeof(ConfigurationRegistration))
                .Select(item => item.ImplementationInstance as ConfigurationRegistration)
                .Where(item => item?.ProviderType == registration?.ProviderType).ToArray();
            Require(contracts.Length <= 1);
            var fields = contracts.SingleOrDefault()?.Contract.Fields ?? [];
            Require(fields.Length <= 256 && fields.All(field => field is not null && Id(field.Key))
                && Unique(fields.Select(field => field.Key)));
            Require(fields.All(field => descriptor.Configuration.Any(requirement => requirement.Key == field.Key
                && requirement.Required == field.Required && requirement.SecretReference == (field.Type == HoardOptionType.Secret))));
            var options = DiscoveryOptionProjector.Project(descriptor, fields, policy);
            Require(policy is null || policy.Options.All(option => options.Any(field => field.Id == option.Id)));
            var compatibility = descriptor.Compatibility;
            var reasons = policy?.Publisher is null || options.Any(option => option.Description is null)
                ? ImmutableArray.Create(new DiscoveryReason("metadata-suppressed", descriptor.Id)) : [];
            modules.Add(new(descriptor.Id, descriptor.Category.ToString().ToLowerInvariant(), descriptor.Version,
                "included", registration is not null, false,
                new(compatibility.HostRange, compatibility.AbstractionsRange,
                    compatibility.AllowPrereleaseHost, compatibility.AllowPrereleaseAbstractions),
                new(descriptor.Provenance.SupportStatus switch
                {
                    ModuleSupportStatus.Fixture => "fixture",
                    ModuleSupportStatus.Community => "community",
                    ModuleSupportStatus.MaintainerSupported => "maintainer-supported",
                    _ => "unknown"
                }, policy?.Publisher),
                "unknown", "unknown", [], options, [], reasons, 0));
        }
        return new(modules.ToImmutable(), contributions.OrderBy(Key, StringComparer.Ordinal).ToImmutableArray(), catalog.ServiceBindings);
    }
}
