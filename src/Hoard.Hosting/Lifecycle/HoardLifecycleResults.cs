using System.Collections.Immutable;

namespace Hoard.Hosting.Lifecycle;

public enum HoardModuleStatus { Disabled, Enabled, Initializing, Ready, NotReady, Failed, Stopping, Stopped }
public enum HoardLifecyclePhase
{
    Registered, Validating, Constructing, ComposingServices, BuildingHost, ComposingRoutes,
    Initializing, AssessingReadiness, Running, Stopping, Draining, CleaningUp, Stopped
}
public enum HoardHealthReason { Ready, Unavailable, Initializing, TimedOut, Failed }
public enum HoardCleanupOutcome { NotEntered, Completed, Failed, TimedOut, NotAttemptedBudgetExhausted, UnsafePendingCallback }
public enum HoardRootDisposalOutcome { Completed, Failed, TimedOut, NotAttemptedBudgetExhausted, NotAttemptedUnsafe, NotAttemptedOwnerPending }
public enum HoardActivityKind { Request, Worker, Build, Phase }

public sealed record HoardHealthObservation(string ResponsibilityId, HoardHealthReason Reason);
public sealed record HoardModuleReadiness(bool Ready, ImmutableArray<HoardHealthObservation> Observations);
public sealed record HoardStartResult(bool Ready, ImmutableArray<HoardLifecycleDiagnostic> Diagnostics);
public sealed record HoardUnsafeActivity(string ModuleId, HoardActivityKind Kind);
public sealed record HoardModuleCleanup(string ModuleId, HoardCleanupOutcome Outcome);
public sealed record HoardStopResult(
    ImmutableArray<HoardLifecycleDiagnostic> Diagnostics,
    ImmutableArray<HoardModuleCleanup> Modules,
    ImmutableArray<HoardUnsafeActivity> UnsafeActivities,
    HoardRootDisposalOutcome RootDisposal,
    int OmittedCount)
{
    public bool Complete => Modules.All(module => module.Outcome is HoardCleanupOutcome.Completed or HoardCleanupOutcome.NotEntered)
        && RootDisposal == HoardRootDisposalOutcome.Completed;
}
