using System.Collections.Immutable;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Microsoft.AspNetCore.Builder;

namespace Hoard.Hosting.Lifecycle;

public sealed class HoardServiceComposition : IAsyncDisposable
{
    internal HoardServiceComposition(HoardValidatedComposition composition,
        ImmutableDictionary<string, HoardModuleOptions>? ownerOptions = null, ImmutableArray<IDisposable> resources = default)
    {
        Composition = composition;
        OwnerOptions = ownerOptions ?? ImmutableDictionary<string, HoardModuleOptions>.Empty;
        this.resources = resources.IsDefault ? [] : resources;
        Coordinator = new(this);
    }

    private readonly ImmutableArray<IDisposable> resources;
    private int releasingInputs;
    internal ImmutableDictionary<string, HoardModuleOptions> OwnerOptions { get; }
    internal void ReleaseInputsWhenQuiescent()
    {
        if (Interlocked.Exchange(ref releasingInputs, 1) != 0) { return; }
        _ = Coordinator.Activities.WhenQuiescent.ContinueWith(_ =>
        {
            foreach (var resource in resources) { resource.Dispose(); }
        }, CancellationToken.None, TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
    }
    internal HoardValidatedComposition Composition { get; }
    internal HoardLifecycleCoordinator Coordinator { get; }
    internal WebApplication? Application { get; set; }
    public IHoardLifecycle Lifecycle => Coordinator;
    public HoardStopResult? StopResult { get; internal set; }
    private readonly object gate = new();
    private Task<HoardStopResult>? disposal;
    private Task? frameworkStop;

    internal Task StopApplicationAsync(CancellationToken cancellationToken = default)
    {
        var modules = Coordinator.StopAsync();
        Task shared;
        lock (gate) { shared = frameworkStop ??= Task.Run(() => StopApplicationCoreAsync(modules)); }
        return shared.WaitAsync(cancellationToken);
    }

    private async Task StopApplicationCoreAsync(Task<HoardStopResult> modules)
    {
        await modules.ConfigureAwait(false);
        var deadline = Coordinator.ShutdownDeadline!;
        if (deadline.Remaining <= TimeSpan.Zero)
        { throw Coordinator.Error("Timeout", "composition", HoardLifecyclePhase.Stopping, true); }
        var activity = Coordinator.Activities.Enter("composition", HoardActivityKind.Phase);
        var observation = new HoardLifecycleCoordinator.CallbackObservation(Coordinator,
            "composition", HoardLifecyclePhase.Stopping, "HostStopFailure", true);
        var work = Task.Run(async () =>
        {
            using (activity) { await observation.RunAsync(() => Application!.StopAsync()).ConfigureAwait(false); }
        });
        HoardLifecycleCoordinator.Observe(work);
        try { await deadline.WaitAsync(work, deadline.Remaining, CancellationToken.None).ConfigureAwait(false); }
        catch (Exception error)
        {
            observation.Abandon();
            if (error is HoardLifecycleException) { throw; }
            throw Coordinator.Error(error is TimeoutException ? "Timeout" : "HostStopFailure",
                "composition", HoardLifecyclePhase.Stopping, true);
        }
    }

    public async ValueTask DisposeAsync()
    {
        Task<HoardStopResult> operation;
        lock (gate) { operation = disposal ??= Task.Run(DisposeCoreAsync); }
        StopResult = await operation.ConfigureAwait(false);
        if (!StopResult.Complete) { throw new HoardLifecycleException(StopResult.Diagnostics); }
    }

    private async Task<HoardStopResult> DisposeCoreAsync()
    {
        var result = await Coordinator.StopAsync().ConfigureAwait(false);
        if (Application is null) { ReleaseInputsWhenQuiescent(); return result; }
        var deadline = Coordinator.ShutdownDeadline!;
        HoardRootDisposalOutcome outcome;
        if (!result.UnsafeActivities.IsEmpty || result.Modules.Any(module => module.Outcome == HoardCleanupOutcome.UnsafePendingCallback))
        { outcome = HoardRootDisposalOutcome.NotAttemptedUnsafe; }
        else if (deadline.Remaining <= TimeSpan.Zero) { outcome = HoardRootDisposalOutcome.NotAttemptedBudgetExhausted; }
        else
        {
            try
            {
                await StopApplicationAsync().ConfigureAwait(false);
                if (deadline.Remaining <= TimeSpan.Zero) { outcome = HoardRootDisposalOutcome.NotAttemptedBudgetExhausted; }
                else
                {
                    var activity = Coordinator.Activities.Enter("composition", HoardActivityKind.Phase);
                    var observation = new HoardLifecycleCoordinator.CallbackObservation(Coordinator,
                        "composition", HoardLifecyclePhase.CleaningUp, "RootDisposalFailure", true);
                    var root = Task.Run(async () =>
                    {
                        using (activity) { await observation.RunAsync(() => Application.DisposeAsync().AsTask()).ConfigureAwait(false); }
                    });
                    HoardLifecycleCoordinator.Observe(root);
                    try
                    {
                        await deadline.WaitAsync(root, deadline.Remaining, CancellationToken.None).ConfigureAwait(false);
                        outcome = HoardRootDisposalOutcome.Completed;
                    }
                    catch (Exception error)
                    {
                        observation.Abandon();
                        outcome = HoardLifecycleCoordinator.CallbackObservation.IsTimeout(error)
                            ? HoardRootDisposalOutcome.TimedOut : HoardRootDisposalOutcome.Failed;
                        if (error is not HoardLifecycleException)
                        {
                            Coordinator.Error(error is TimeoutException ? "Timeout" : "RootDisposalFailure",
                                "composition", HoardLifecyclePhase.CleaningUp, true);
                        }
                    }
                }
            }
            catch (HoardLifecycleException)
            {
                outcome = HoardRootDisposalOutcome.NotAttemptedUnsafe;
            }
        }
        ReleaseInputsWhenQuiescent();
        return result with { RootDisposal = outcome, Diagnostics = Coordinator.Snapshot.Diagnostics, OmittedCount = Coordinator.Snapshot.OmittedCount };
    }
}
