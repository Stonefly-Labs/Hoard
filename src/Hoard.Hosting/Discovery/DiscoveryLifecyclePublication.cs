using System.Collections.Immutable;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Discovery;

internal sealed record DiscoveryModuleState(string Id, string Phase, string Readiness);
internal sealed record DiscoveryPublishedState(Guid LifecycleId, ulong Revision, DateTimeOffset PublishedAt,
    DateTimeOffset? ReadinessAssessedAt, string Phase, bool Ready, bool StartupAdmission,
    ImmutableArray<DiscoveryModuleState> Modules, ImmutableArray<DiscoveryReason> Reasons, int OmittedReasonCount);

internal sealed class DiscoveryLifecyclePublication(DiscoveryRegistration registration, Guid lifecycleId)
{
    private DiscoveryPublishedState? current;
    private ulong revision;
    internal DiscoveryPublishedState? Capture() => Volatile.Read(ref current);

    internal void Publish(HoardLifecyclePhase phase, bool admission, bool ready, DateTimeOffset? assessed,
        IEnumerable<HoardLifecycleCoordinator.Entry> entries, IReadOnlyList<HoardLifecycleDiagnostic> diagnostics, int omitted)
    {
        var modules = entries.Select(entry => new DiscoveryModuleState(entry.Registration.Declaration.Id,
            Phase(entry.Phase), Status(entry.Status))).ToImmutableArray();
        var known = registration.Frozen!.Modules;
        var reasons = diagnostics.Select(diagnostic => new DiscoveryReason(diagnostic.RuleCode switch
        {
            "NotReady" or "InvalidReadiness" => "not-ready",
            "Timeout" => "deadline",
            "Cancelled" => "cancelled",
            "TerminalLifecycle" => "stopped",
            _ => "observation-unavailable"
        }, known.Any(module => module.Id == diagnostic.ModuleId) ? diagnostic.ModuleId : null,
            correlationId: diagnostic.CorrelationId)).OrderBy(reason => reason.Code, StringComparer.Ordinal)
            .ThenBy(reason => reason.ModuleId, StringComparer.Ordinal).ToImmutableArray();
        var next = new DiscoveryPublishedState(lifecycleId, checked(++revision),
            registration.Options.TimeProvider.GetUtcNow(), assessed, Phase(phase), ready, admission, modules, reasons, omitted);
        Volatile.Write(ref current, next);
    }

    internal static string Phase(HoardLifecyclePhase phase) => phase switch
    {
        HoardLifecyclePhase.Registered => "registered",
        HoardLifecyclePhase.Validating => "validating",
        HoardLifecyclePhase.Constructing => "constructing",
        HoardLifecyclePhase.ComposingServices => "composing-services",
        HoardLifecyclePhase.BuildingHost => "building-host",
        HoardLifecyclePhase.ComposingRoutes => "composing-routes",
        HoardLifecyclePhase.Initializing => "initializing",
        HoardLifecyclePhase.AssessingReadiness => "assessing-readiness",
        HoardLifecyclePhase.Running => "running",
        HoardLifecyclePhase.Stopping => "stopping",
        HoardLifecyclePhase.Draining => "draining",
        HoardLifecyclePhase.CleaningUp => "cleaning-up",
        HoardLifecyclePhase.Stopped => "stopped",
        _ => "unknown"
    };

    private static string Status(HoardModuleStatus status) => status switch
    {
        HoardModuleStatus.Disabled => "disabled",
        HoardModuleStatus.Enabled => "enabled",
        HoardModuleStatus.Initializing => "initializing",
        HoardModuleStatus.Ready => "ready",
        HoardModuleStatus.NotReady => "not-ready",
        HoardModuleStatus.Failed => "failed",
        HoardModuleStatus.Stopping => "stopping",
        HoardModuleStatus.Stopped => "stopped",
        _ => "unknown"
    };
}
