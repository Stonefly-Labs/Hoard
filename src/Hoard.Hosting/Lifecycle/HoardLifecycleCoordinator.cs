using System.Collections.Immutable;
using Hoard.Hosting.Composition;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Hosting.Lifecycle;

internal sealed class HoardLifecycleCoordinator : IHoardLifecycle
{
    internal sealed class Entry(HoardModuleRegistration registration)
    {
        internal HoardModuleRegistration Registration { get; } = registration;
        internal IHoardModule? Module { get; set; }
        internal HoardModuleStatus Status { get; set; } = HoardModuleStatus.Enabled;
        internal HoardLifecyclePhase Phase { get; set; } = HoardLifecyclePhase.Registered;
        internal ImmutableArray<HoardHealthObservation> Health { get; set; } = [];
    }

    internal sealed class CallbackObservation(HoardLifecycleCoordinator coordinator, string owner,
        HoardLifecyclePhase at, string failureCode, bool cleanup = false)
    {
        private int abandoned;
        internal void Abandon() => Volatile.Write(ref abandoned, 1);
        internal static bool IsTimeout(Exception error) => error is TimeoutException
            || error is HoardLifecycleException failure && failure.Diagnostics.Any(item => item.RuleCode == "Timeout");

        internal async Task<T> RunAsync<T>(Func<Task<T>> callback)
        {
            try { return await callback().ConfigureAwait(false); }
            catch (Exception error) when (error is not HoardLifecycleException and not OperationCanceledException)
            {
                var late = Volatile.Read(ref abandoned) != 0;
                throw coordinator.Error(late ? "LateCallbackFailure" :
                    error is TimeoutException ? "Timeout" : failureCode, owner, at, cleanup || late);
            }
        }

        internal Task RunAsync(Func<Task> callback) => RunAsync(async () =>
        { await callback().ConfigureAwait(false); return true; });
    }

    internal object Gate { get; } = new();
    internal HoardActivityTracker Activities { get; } = new();
    internal ActivationLedger Ledger { get; } = new();
    internal HoardServiceComposition Lease { get; }
    internal HoardValidatedComposition Composition => Lease.Composition;
    internal HoardLifecycleOptions Options => Composition.Options;
    internal LifecycleDeadline StartupDeadline { get; }
    internal Dictionary<string, Entry> Entries { get; }
    private readonly CancellationTokenSource lifetime = new();
    private readonly List<HoardLifecycleDiagnostic> diagnostics = [];
    private readonly Guid correlation = Guid.NewGuid();
    private Task<HoardStartResult>? start;
    private Task<HoardStopResult>? stop;
    private Task<HoardLifecycleSnapshot>? assessment;
    private int omitted;
    private bool stopping;
    private bool admission;
    private bool ready;
    private bool mapped;
    private HoardLifecyclePhase phase = HoardLifecyclePhase.Registered;
    internal Action? VerifyRoutes { get; set; }
    internal LifecycleDeadline? ShutdownDeadline { get; private set; }

    internal HoardLifecycleCoordinator(HoardServiceComposition lease)
    {
        Lease = lease;
        StartupDeadline = new(Composition.Clock, Options.StartupTimeout);
        Entries = Composition.Registrations.Where(r => Composition.EnabledModuleIds.Contains(r.Declaration.Id))
            .ToDictionary(r => r.Declaration.Id, r => new Entry(r), StringComparer.Ordinal);
    }

    public HoardLifecycleSnapshot Snapshot
    {
        get
        {
            lock (Gate)
            {
                return new(correlation, Composition.Identity, phase, admission, ready,
                    Composition.Registrations.Select(registration =>
                    {
                        var id = registration.Declaration.Id;
                        return Entries.TryGetValue(id, out var entry)
                            ? new HoardModuleObservation(id, true, true, entry.Status, entry.Phase, entry.Health)
                            : new(id, true, false, HoardModuleStatus.Disabled, HoardLifecyclePhase.Registered, []);
                    }).ToImmutableArray(), diagnostics.ToImmutableArray(), omitted);
            }
        }
    }

    internal HoardLifecycleException Error(string code, string owner, HoardLifecyclePhase at,
        bool cleanup = false, IEnumerable<string>? path = null)
    {
        lock (Gate)
        {
            var diagnostic = new HoardLifecycleDiagnostic(code, owner, at, correlation, cleanup, path);
            if (diagnostics.Count < 100) { diagnostics.Add(diagnostic); } else { omitted++; }
            return new([diagnostic]);
        }
    }

    internal void CheckCanDispatch(string owner, HoardLifecyclePhase at)
    {
        if (stopping) { throw Error("Cancelled", owner, at); }
        if (StartupDeadline.Remaining <= TimeSpan.Zero) { throw Error("Timeout", owner, at); }
    }

    internal async Task InvokeStartupAsync(string owner, HoardLifecyclePhase at, Func<CancellationToken, Task> callback,
        TimeSpan? cap = null)
    {
        Task work;
        var observation = new CallbackObservation(this, owner, at, "PhaseFailure");
        lock (Gate)
        {
            CheckCanDispatch(owner, at);
            phase = at;
            if (Entries.TryGetValue(owner, out var entry)) { entry.Phase = at; }
            Ledger.Enter(owner, at);
            var activity = Activities.Enter(owner, at == HoardLifecyclePhase.BuildingHost ? HoardActivityKind.Build : HoardActivityKind.Phase);
            var token = lifetime.Token;
            work = Task.Run(async () =>
            {
                using (activity)
                { await observation.RunAsync(() => callback(token)).ConfigureAwait(false); }
            });
            Observe(work);
        }
        try
        {
            await StartupDeadline.WaitAsync(work, cap ?? Options.ActivationCallbackTimeout, lifetime.Token).ConfigureAwait(false);
            lock (Gate) { CheckCanDispatch(owner, at); }
        }
        catch (HoardLifecycleException) { throw; }
        catch (Exception error)
        {
            observation.Abandon();
            throw Error(error is TimeoutException ? "Timeout" :
                error is OperationCanceledException ? "Cancelled" : "PhaseFailure", owner, at);
        }
    }

    // Callback diagnostics are recorded before their tracked activity is released.
    internal static void Observe(Task task) =>
        _ = task.ContinueWith(completed =>
        {
            _ = completed.Exception;
        }, CancellationToken.None, TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);

    private void CancelPending(CancellationTokenSource source, Task? work, string owner, HoardLifecyclePhase at)
    {
        var activity = Activities.Enter(owner, HoardActivityKind.Phase);
        _ = Task.Run(async () =>
        {
            using (activity)
            {
                try { await source.CancelAsync().ConfigureAwait(false); }
                catch (ObjectDisposedException) when (work?.IsCompleted == true) { return; }
                catch (Exception) { Error("CancellationFailure", owner, at, true); }
            }
        });
    }

    internal void MarkMapped()
    {
        lock (Gate) { CheckCanDispatch("composition", HoardLifecyclePhase.ComposingRoutes); mapped = true; }
    }

    public Task<HoardStartResult> StartAsync(CancellationToken cancellationToken = default)
    {
        lock (Gate)
        {
            if (stopping) { return Task.FromResult(new HoardStartResult(false, Error("TerminalLifecycle", "composition", phase).Diagnostics)); }
            start ??= Task.Run(StartCoreAsync);
            return start.WaitAsync(cancellationToken);
        }
    }

    private async Task<HoardStartResult> StartCoreAsync()
    {
        try
        {
            lock (Gate)
            {
                CheckCanDispatch("composition", HoardLifecyclePhase.Initializing);
                if (!mapped || Lease.Application is null) { throw Error("MissingMapping", "composition", phase); }
            }
            await InvokeStartupAsync("composition", HoardLifecyclePhase.Validating, _ =>
            { VerifyRoutes!(); return Task.CompletedTask; }).ConfigureAwait(false);
            foreach (var id in Composition.ActivationOrder)
            {
                lock (Gate) { Entries[id].Status = HoardModuleStatus.Initializing; }
                await InvokeStartupAsync(id, HoardLifecyclePhase.Initializing,
                    token => Entries[id].Module!.InitializeAsync(Lease.Application!.Services, token).AsTask()).ConfigureAwait(false);
            }
            await AssessCoreAsync(true).ConfigureAwait(false);
            lock (Gate)
            {
                CheckCanDispatch("composition", HoardLifecyclePhase.Running);
                if (!ready) { throw Error("NotReady", "composition", HoardLifecyclePhase.AssessingReadiness); }
                admission = true;
                phase = HoardLifecyclePhase.Running;
                foreach (var id in Composition.ActivationOrder)
                {
                    if (stopping) { break; }
                    Ledger.Enter(id, HoardLifecyclePhase.Running);
                    var activity = Activities.Enter(id, HoardActivityKind.Worker);
                    var work = Task.Run(async () =>
                    {
                        using (activity)
                        {
                            try { await Entries[id].Module!.RunAsync(lifetime.Token).ConfigureAwait(false); }
                            catch (OperationCanceledException) when (lifetime.IsCancellationRequested) { }
                            catch (Exception)
                            {
                                lock (Gate)
                                {
                                    if (stopping) { Error("LateCallbackFailure", id, HoardLifecyclePhase.Running, true); }
                                    else
                                    {
                                        Entries[id].Status = HoardModuleStatus.Failed;
                                        ready = admission = false;
                                        Error("WorkerFailure", id, HoardLifecyclePhase.Running);
                                        var notificationActivity = Activities.Enter("composition", HoardActivityKind.Phase);
                                        _ = StopAsync();
                                        var notification = Task.Run(() =>
                                        {
                                            using (notificationActivity)
                                            {
                                                try
                                                {
                                                    Lease.Application!.Services.GetRequiredService<IHostApplicationLifetime>().StopApplication();
                                                }
                                                catch (Exception)
                                                { throw Error("HostStopFailure", "composition", HoardLifecyclePhase.Stopping, true); }
                                            }
                                        });
                                        Observe(notification);
                                    }
                                }
                            }
                        }
                    });
                    Observe(work);
                }
                return new(true, diagnostics.ToImmutableArray());
            }
        }
        catch (HoardLifecycleException)
        {
            lock (Gate) { ready = admission = false; }
            await StopAsync().ConfigureAwait(false);
            return new(false, Snapshot.Diagnostics);
        }
    }

    public Task<HoardLifecycleSnapshot> AssessReadinessAsync(CancellationToken cancellationToken = default)
    {
        lock (Gate)
        {
            if (stopping || !admission) { return Task.FromResult(Snapshot); }
            if (assessment is null || assessment.IsCompleted) { assessment = Task.Run(() => AssessCoreAsync(false)); }
            return assessment.WaitAsync(cancellationToken);
        }
    }

    private async Task<HoardLifecycleSnapshot> AssessCoreAsync(bool initial)
    {
        var deadline = new LifecycleDeadline(Composition.Clock,
            initial ? StartupDeadline.Cap(Options.ReadinessTimeout) : Options.ReadinessTimeout);
        var results = new Dictionary<string, HoardModuleReadiness>(StringComparer.Ordinal);
        var probes = new List<Task>();
        var timeout = new CancellationTokenSource();
        var linked = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token, timeout.Token);
        try
        {
            foreach (var id in Composition.ActivationOrder)
            {
                Task<HoardModuleReadiness> work;
                var observation = new CallbackObservation(this, id, HoardLifecyclePhase.AssessingReadiness, "InvalidReadiness");
                lock (Gate)
                {
                    if (stopping) { return Snapshot; }
                    if (deadline.Remaining <= TimeSpan.Zero)
                    {
                        Error("Timeout", id, HoardLifecyclePhase.AssessingReadiness);
                        break;
                    }
                    if (initial) { phase = Entries[id].Phase = HoardLifecyclePhase.AssessingReadiness; Ledger.Enter(id, phase); }
                    var activity = Activities.Enter(id, HoardActivityKind.Phase);
                    work = Task.Run(async () =>
                    {
                        using (activity)
                        {
                            return await observation.RunAsync(() => Entries[id].Module!.CheckReadinessAsync(linked.Token).AsTask()).ConfigureAwait(false);
                        }
                    });
                    Observe(work);
                    probes.Add(work);
                }
                try
                {
                    await deadline.WaitAsync(work, Options.ReadinessTimeout, lifetime.Token).ConfigureAwait(false);
                    var result = await work.ConfigureAwait(false);
                    if (!HoardReadinessEvaluator.Valid(Entries[id].Registration.Declaration, result))
                    { throw Error("InvalidReadiness", id, HoardLifecyclePhase.AssessingReadiness); }
                    results.Add(id, result);
                }
                catch (Exception error)
                {
                    observation.Abandon();
                    if (CallbackObservation.IsTimeout(error) || error is OperationCanceledException)
                    {
                        CancelPending(timeout, work, id, HoardLifecyclePhase.AssessingReadiness);
                    }
                    if (error is not HoardLifecycleException)
                    { Error(error is TimeoutException ? "Timeout" : error is OperationCanceledException ? "Cancelled" : "InvalidReadiness", id, HoardLifecyclePhase.AssessingReadiness); }
                    results[id] = new(false, []);
                    if (initial) { break; }
                }
            }
            lock (Gate)
            {
                if (stopping) { return Snapshot; }
                ready = results.Count == Entries.Count && results.Values.All(result => result.Ready);
                foreach (var (id, result) in results)
                {
                    Entries[id].Status = result.Ready ? HoardModuleStatus.Ready : HoardModuleStatus.NotReady;
                    Entries[id].Health = result.Observations;
                    if (!result.Ready) { Error("NotReady", id, HoardLifecyclePhase.AssessingReadiness); }
                }
                return Snapshot;
            }
        }
        finally
        {
            var activity = Activities.Enter("composition", HoardActivityKind.Phase);
            var observation = new CallbackObservation(this, "composition", HoardLifecyclePhase.AssessingReadiness, "CleanupFailure", true);
            var disposal = Task.WhenAll(probes).ContinueWith(completed =>
            {
                _ = completed.Exception;
                return DisposeSourcesAsync();
            }, CancellationToken.None, TaskContinuationOptions.None, TaskScheduler.Default).Unwrap();
            Observe(disposal);
            async Task DisposeSourcesAsync()
            {
                using (activity)
                {
                    await observation.RunAsync(() =>
                    { linked.Dispose(); timeout.Dispose(); return Task.CompletedTask; }).ConfigureAwait(false);
                }
            }
        }
    }

    public Task<HoardStopResult> StopAsync(CancellationToken cancellationToken = default)
    {
        lock (Gate)
        {
            if (stop is null)
            {
                stopping = true;
                admission = ready = false;
                phase = HoardLifecyclePhase.Stopping;
                ShutdownDeadline = new(Composition.Clock, Options.ShutdownTimeout);
                stop = Task.Run(StopCoreAsync);
            }
            return stop.WaitAsync(cancellationToken);
        }
    }

    private async Task<HoardStopResult> StopCoreAsync()
    {
        var deadline = ShutdownDeadline!;
        CancelPending(lifetime, null, "composition", HoardLifecyclePhase.Stopping);
        lock (Gate) { phase = HoardLifecyclePhase.Draining; }
        try { await deadline.WaitAsync(Activities.WhenQuiescent, Options.DrainTimeout, CancellationToken.None).ConfigureAwait(false); }
        catch (TimeoutException) { Error("Timeout", "composition", HoardLifecyclePhase.Draining, true); }
        var outcomes = ImmutableArray.CreateBuilder<HoardModuleCleanup>();
        foreach (var id in Composition.ActivationOrder.Reverse())
        {
            var entry = Entries[id];
            if (entry.Module is null) { outcomes.Add(new(id, HoardCleanupOutcome.NotEntered)); continue; }
            lock (Gate) { phase = entry.Phase = HoardLifecyclePhase.CleaningUp; entry.Status = HoardModuleStatus.Stopping; }
            if (HoardCleanupPlanner.Unsafe(id, Activities.Snapshot(), Composition))
            {
                outcomes.Add(new(id, HoardCleanupOutcome.UnsafePendingCallback));
                Error("UnsafePendingCallback", id, phase, true);
                continue;
            }
            if (deadline.Remaining <= TimeSpan.Zero)
            {
                outcomes.Add(new(id, HoardCleanupOutcome.NotAttemptedBudgetExhausted));
                Error("Timeout", id, phase, true);
                continue;
            }
            var activity = Activities.Enter(id, HoardActivityKind.Phase);
            var timeout = new CancellationTokenSource();
            var observation = new CallbackObservation(this, id, HoardLifecyclePhase.CleaningUp, "CleanupFailure", true);
            Ledger.Enter(id, HoardLifecyclePhase.CleaningUp);
            var task = Task.Run(async () =>
            {
                using (activity)
                using (timeout)
                { await observation.RunAsync(() => entry.Module.StopAsync(timeout.Token).AsTask()).ConfigureAwait(false); }
            });
            Observe(task);
            try
            {
                await deadline.WaitAsync(task, Options.ModuleCleanupTimeout, CancellationToken.None).ConfigureAwait(false);
                outcomes.Add(new(id, HoardCleanupOutcome.Completed));
                lock (Gate) { entry.Status = HoardModuleStatus.Stopped; }
            }
            catch (Exception error)
            {
                observation.Abandon();
                if (CallbackObservation.IsTimeout(error))
                {
                    CancelPending(timeout, task, id, HoardLifecyclePhase.CleaningUp);
                }
                var outcome = CallbackObservation.IsTimeout(error) || error is OperationCanceledException
                    ? HoardCleanupOutcome.TimedOut : HoardCleanupOutcome.Failed;
                outcomes.Add(new(id, outcome));
                if (error is not HoardLifecycleException)
                { Error(outcome == HoardCleanupOutcome.TimedOut ? "Timeout" : "CleanupFailure", id, HoardLifecyclePhase.CleaningUp, true); }
            }
        }
        var root = !Activities.Snapshot().IsEmpty || outcomes.Any(item => item.Outcome == HoardCleanupOutcome.UnsafePendingCallback)
            ? HoardRootDisposalOutcome.NotAttemptedUnsafe
            : Lease.Application is null ? HoardRootDisposalOutcome.Completed : HoardRootDisposalOutcome.NotAttemptedOwnerPending;
        lock (Gate)
        {
            phase = HoardLifecyclePhase.Stopped;
            var result = new HoardStopResult(diagnostics.ToImmutableArray(), outcomes.ToImmutable(), Activities.Snapshot(), root, omitted);
            return result;
        }
    }

    internal IDisposable? TryAdmit(string owner)
    {
        lock (Gate) { return admission && !stopping ? Activities.Enter(owner, HoardActivityKind.Request) : null; }
    }
}
