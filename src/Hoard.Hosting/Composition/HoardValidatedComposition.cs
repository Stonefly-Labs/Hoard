using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Composition;

public sealed record HoardDependencyEdge(string PrerequisiteId, string DependentId,
    bool Optional, string VersionRange, bool AllowPrerelease);

public sealed class HoardValidatedComposition
{
    internal HoardValidatedComposition(HoardBuilder builder, HoardStartupSelection selection,
        HoardPlatformVersions versions, HoardLifecycleOptions options, TimeProvider clock,
        ImmutableArray<HoardModuleRegistration> registrations,
        ImmutableArray<HoardModuleLifecycleRegistration> adapters, ImmutableArray<string> order,
        ImmutableArray<HoardDependencyEdge> edges)
    {
        Builder = builder;
        Selection = selection;
        PlatformVersions = versions;
        Options = options;
        Clock = clock;
        Registrations = registrations;
        Adapters = adapters;
        ActivationOrder = order;
        ActiveEdges = edges;
        ServiceSnapshot = builder.Services.ToImmutableArray();
        DisabledDeclarations = registrations.Where(r => !selection.EnabledModuleIds.Contains(r.Declaration.Id))
            .Select(r => r.Declaration).ToImmutableArray();
    }

    public Guid Identity { get; } = Guid.NewGuid();
    public ImmutableArray<string> EnabledModuleIds => Selection.EnabledModuleIds;
    public ImmutableArray<ModuleDescriptor> DisabledDeclarations { get; }
    public string MetadataModuleId => Selection.MetadataModuleId;
    public string ArtifactModuleId => Selection.ArtifactModuleId;
    public HoardPlatformVersions PlatformVersions { get; }
    public ImmutableArray<HoardRequiredCapability> SatisfiedCapabilities => Selection.RequiredCapabilities;
    public ImmutableArray<HoardDependencyEdge> ActiveEdges { get; }
    public ImmutableArray<string> ActivationOrder { get; }
    internal HoardBuilder Builder { get; }
    internal HoardStartupSelection Selection { get; }
    internal HoardLifecycleOptions Options { get; }
    internal TimeProvider Clock { get; }
    internal ImmutableArray<HoardModuleRegistration> Registrations { get; }
    internal ImmutableArray<HoardModuleLifecycleRegistration> Adapters { get; }
    internal ImmutableArray<ServiceDescriptor> ServiceSnapshot { get; }
    internal bool Consumed { get; set; }
}
