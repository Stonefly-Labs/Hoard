using Hoard.Hosting.Composition;
using Microsoft.AspNetCore.Builder;

namespace Hoard.Hosting.Lifecycle;

public sealed class HoardServiceComposition : IAsyncDisposable
{
    internal HoardServiceComposition(HoardValidatedComposition composition)
    {
        Composition = composition;
        Coordinator = new(this);
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
        var work = Task.Run(async () =>
        {
            using (activity) { await Application!.StopAsync().ConfigureAwait(false); }
        });
        Coordinator.Observe(work);
        try { await deadline.WaitAsync(work, deadline.Remaining, CancellationToken.None).ConfigureAwait(false); }
        catch (Exception error)
        {
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
        if (Application is null) { return result; }
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
                var root = Task.Run(async () => await Application.DisposeAsync().ConfigureAwait(false));
                Coordinator.Observe(root);
                try
                {
                    await deadline.WaitAsync(root, deadline.Remaining, CancellationToken.None).ConfigureAwait(false);
                    outcome = HoardRootDisposalOutcome.Completed;
                }
                catch (Exception error)
                {
                    outcome = error is TimeoutException ? HoardRootDisposalOutcome.TimedOut : HoardRootDisposalOutcome.Failed;
                    Coordinator.Error(error is TimeoutException ? "Timeout" : "RootDisposalFailure", "composition", HoardLifecyclePhase.CleaningUp, true);
                }
            }
            catch (HoardLifecycleException)
            {
                outcome = HoardRootDisposalOutcome.NotAttemptedUnsafe;
            }
        }
        return result with { RootDisposal = outcome, Diagnostics = Coordinator.Snapshot.Diagnostics, OmittedCount = Coordinator.Snapshot.OmittedCount };
    }
}
