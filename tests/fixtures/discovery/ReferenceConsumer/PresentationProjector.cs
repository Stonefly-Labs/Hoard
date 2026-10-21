using System.Collections.Immutable;

namespace Hoard.Discovery.ReferenceConsumer;

public sealed record SemanticLine(int Order, string Label, string Text);
public sealed record ConsumerAction(string OperationId, string AccessibleName, bool Hidden, bool Enabled, string Explanation);
public sealed record ModulePresentation(string Id, ImmutableArray<SemanticLine> ReadingOrder, ImmutableArray<ConsumerAction> Actions);

public static class PresentationProjector
{
    public static string Lookup(ConsumerObservation observation, string moduleId) =>
        observation.Modules.Any(module => module.Id == moduleId) ? "Known module"
            : observation.Completeness == "complete" ? "Not included. " + PresentationText.Custom
            : "Inclusion unknown. " + PresentationText.Unknown;

    public static ImmutableArray<ModulePresentation> Project(ConsumerObservation observation, bool current,
        IReadOnlySet<string> executionPermissions)
    {
        return observation.Modules.Select(module =>
        {
            var lines = ImmutableArray.CreateBuilder<SemanticLine>();
            void Line(string label, string text) => lines.Add(new(lines.Count + 1, $"{module.Id}: {label}", text));
            Line("inclusion", module.Inclusion == "included" ? "Included" : "Inclusion unknown");
            Line("registration", module.Registered ? "Registered" :
                (module.Inclusion == "included" ? "Included, not registered. " : "Not registered. ") + PresentationText.Custom);
            Line("enablement", module.Enabled ? "Enabled selection" : "Disabled. " + PresentationText.Bundled);
            Line("observed readiness", module.Understood ? module.Readiness : "Unknown/uninterpretable");
            Line("authority phase", module.Phase);
            Line("captured", observation.CapturedAt.ToString("O"));
            Line("published", observation.PublishedAt.ToString("O"));
            Line("assessed", observation.AssessedAt?.ToString("O") ?? "Not yet assessed");
            foreach (var reason in module.Reasons) { Line(reason.Code, reason.CorrectiveAction); }
            var actions = module.Capabilities.Select(capability =>
            {
                var known = module.Id == "protocol" && capability is { Id: "inspect", Version: "0.1.0", OperationId: "inspect" }
                    && capability.Owners.SequenceEqual(["protocol"]) && capability.Understood && module.Understood;
                var supported = known && capability.Support == "supported";
                var ownersReady = capability.Owners.Concat(capability.Dependencies).All(id =>
                    observation.Modules.Any(owner => owner.Id == id && owner.Understood
                        && owner.Registered && owner.Enabled && owner.Readiness == "ready"));
                var enabled = supported && current && observation.HostPhase == "running" && observation.StartupAdmission
                    && ownersReady && capability.Reasons.IsEmpty && capability.Availability == "usable"
                    && executionPermissions.Contains(capability.OperationId);
                Line($"{capability.OperationId} support", capability.EvidenceScope == "fixture" ? PresentationText.Fixture : capability.Support);
                Line($"{capability.OperationId} availability", capability.Availability);
                foreach (var reason in capability.Reasons) { Line($"{capability.OperationId}: {reason.Code}", reason.CorrectiveAction); }
                return new ConsumerAction(capability.OperationId, $"{module.Id}: {capability.OperationId}", !supported, enabled,
                    !current ? "Observation is not current; refresh before acting."
                    : !executionPermissions.Contains(capability.OperationId) ? "Separate execution permission is required."
                    : enabled ? "Availability is observed; execution must still authorize independently."
                    : capability.Reasons.FirstOrDefault()?.CorrectiveAction ?? PresentationText.Runtime);
            }).ToImmutableArray();
            return new ModulePresentation(module.Id, lines.ToImmutable(), actions);
        }).ToImmutableArray();
    }
}
