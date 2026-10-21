using System.Collections.Immutable;

namespace Hoard.Hosting.Discovery;

public sealed record HoardDiscoveryObservation(
    string DistributionId, string DistributionVersion, string InventoryCompleteness,
    Guid LifecycleId, ulong Revision, DateTimeOffset CapturedAt, DateTimeOffset PublishedAt,
    DateTimeOffset? ReadinessAssessedAt, string Phase, bool Ready, bool StartupAdmission,
    ImmutableArray<DiscoveryModule> Modules, ImmutableArray<DiscoveryReason> Reasons, int OmittedReasonCount);

public sealed record DiscoveryModule(string Id, string Category, string Version, string Inclusion,
    bool Registered, bool Enabled, DiscoveryCompatibility Compatibility, DiscoveryProvenance Provenance,
    string LifecyclePhase, string Readiness, ImmutableArray<string> SelectedRoles,
    ImmutableArray<DiscoveryOption> Options, ImmutableArray<DiscoveryCapability> Capabilities,
    ImmutableArray<DiscoveryReason> Reasons, int OmittedReasonCount);

public sealed record DiscoveryCompatibility(string HostRange, string AbstractionsRange,
    bool AllowHostPrerelease, bool AllowAbstractionsPrerelease);
public sealed record DiscoveryProvenance(string Classification, string? Publisher);
public sealed record DiscoveryConstraints(int MinimumLength, int MaximumLength, string Minimum, string Maximum);
public sealed record DiscoveryOption(string Id, string Type, bool Required, bool Secret,
    string? Description, DiscoveryConstraints? Constraints, string? PublicDefault, ImmutableArray<string>? AllowedValues);
public sealed record DiscoveryCapability(string Id, string Version, string OperationId,
    ImmutableArray<string> Owners, ImmutableArray<string> Dependencies, string Support, string EvidenceScope,
    ImmutableArray<string> EvidenceIds, string Availability, ImmutableArray<DiscoveryReason> Reasons, int OmittedReasonCount);
