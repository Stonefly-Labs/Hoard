using System.Collections.Immutable;
using System.Globalization;
using Hoard.Application.Discovery;
using Hoard.Hosting.Discovery;

namespace Hoard.Application.Features.Modules.GetDiscovery;

internal static class Projector
{
    internal static Response Project(HoardDiscoveryObservation source, DiscoveryResponseWriter.Budget budget) =>
        new(1, new(source.DistributionId, source.DistributionVersion, source.InventoryCompleteness),
            new(source.LifecycleId, source.Revision.ToString(CultureInfo.InvariantCulture), source.CapturedAt,
                source.PublishedAt, source.ReadinessAssessedAt), new(source.Phase, source.Ready, source.StartupAdmission),
            Map(source.Modules, module => new Module(module.Id, module.Category, module.Version, module.Inclusion,
                module.Registered, module.Enabled, new(module.Compatibility.HostRange, module.Compatibility.AbstractionsRange,
                    module.Compatibility.AllowHostPrerelease, module.Compatibility.AllowAbstractionsPrerelease),
                new(module.Provenance.Classification, module.Provenance.Publisher), module.LifecyclePhase, module.Readiness,
                module.SelectedRoles, Map(module.Options, option => new Option(option.Id, option.Type, option.Required,
                    option.Secret, option.Description, option.Constraints is { } constraints
                        ? new(constraints.MinimumLength, constraints.MaximumLength, constraints.Minimum, constraints.Maximum) : null,
                    option.PublicDefault, option.AllowedValues), budget),
                Map(module.Capabilities, capability => new Capability(capability.Id, capability.Version, capability.OperationId,
                    capability.Owners, capability.Dependencies, capability.Support, capability.EvidenceScope, capability.EvidenceIds,
                    capability.Availability, Map(capability.Reasons, Reason, budget), capability.OmittedReasonCount), budget),
                Map(module.Reasons, Reason, budget), module.OmittedReasonCount), budget),
            Map(source.Reasons, Reason, budget), source.OmittedReasonCount);

    private static Reason Reason(DiscoveryReason reason) =>
        new(reason.Code, reason.CorrectiveAction, reason.ModuleId, reason.OperationId, reason.CorrelationId);

    private static ImmutableArray<TResult> Map<TSource, TResult>(ImmutableArray<TSource> input,
        Func<TSource, TResult> project, DiscoveryResponseWriter.Budget budget)
    {
        var result = ImmutableArray.CreateBuilder<TResult>(input.Length);
        foreach (var item in input) { budget.Check(); result.Add(project(item)); }
        return result.ToImmutable();
    }
}
