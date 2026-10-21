using System.Collections.Immutable;
using System.Text.Json.Serialization;

namespace Hoard.Application.Features.Modules.GetDiscovery;

internal sealed record Response(int SchemaVersion, Distribution Distribution, Observation Observation, Host Host,
    ImmutableArray<Module> Modules, ImmutableArray<Reason> Reasons, int OmittedReasonCount);
internal sealed record Distribution(string Id, string Version, string InventoryCompleteness);
internal sealed record Observation(Guid LifecycleId, string Revision, DateTimeOffset CapturedAt, DateTimeOffset PublishedAt,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.Never)] DateTimeOffset? ReadinessAssessedAt);
internal sealed record Host(string Phase, bool Ready, bool StartupAdmission);
internal sealed record Module(string Id, string Category, string Version, string Inclusion, bool Registered, bool Enabled,
    Compatibility Compatibility, Provenance Provenance, string LifecyclePhase, string Readiness, ImmutableArray<string> SelectedRoles,
    ImmutableArray<Option> Options, ImmutableArray<Capability> Capabilities, ImmutableArray<Reason> Reasons, int OmittedReasonCount);
internal sealed record Compatibility(string HostRange, string AbstractionsRange, bool AllowHostPrerelease, bool AllowAbstractionsPrerelease);
internal sealed record Provenance(string Classification, string? Publisher);
internal sealed record Constraints(int MinimumLength, int MaximumLength, string Minimum, string Maximum);
internal sealed record Option(string Id, string Type, bool Required, bool Secret, string? Description, Constraints? Constraints,
    string? PublicDefault, ImmutableArray<string>? AllowedValues);
internal sealed record Capability(string Id, string Version, string OperationId, ImmutableArray<string> Owners,
    ImmutableArray<string> Dependencies, string Support, string EvidenceScope, ImmutableArray<string> EvidenceIds,
    string Availability, ImmutableArray<Reason> Reasons, int OmittedReasonCount);
internal sealed record Reason(string Code, string CorrectiveAction, string? ModuleId, string? OperationId, Guid? CorrelationId);
