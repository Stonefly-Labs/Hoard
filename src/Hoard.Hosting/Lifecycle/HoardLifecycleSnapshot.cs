using System.Collections.Immutable;

namespace Hoard.Hosting.Lifecycle;

public sealed record HoardModuleObservation(string ModuleId, bool IncludedByRegistration, bool Enabled,
    HoardModuleStatus Status, HoardLifecyclePhase Phase, ImmutableArray<HoardHealthObservation> Health);

public sealed record HoardLifecycleSnapshot(Guid CorrelationId, Guid CompositionIdentity,
    HoardLifecyclePhase Phase, bool StartupAdmission, bool Ready,
    ImmutableArray<HoardModuleObservation> Modules, ImmutableArray<HoardLifecycleDiagnostic> Diagnostics,
    int OmittedCount);
