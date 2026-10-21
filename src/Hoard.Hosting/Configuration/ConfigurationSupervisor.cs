using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using System.Diagnostics.Metrics;

namespace Hoard.Hosting.Configuration;

internal sealed class ConfigurationSupervisor
{
    private static readonly Meter Meter = new("Hoard.Configuration");
    private static readonly Counter<long> Events = Meter.CreateCounter<long>("hoard.configuration.events");
    private readonly object gate = new();
    private readonly HoardConfigurationOptions options;
    private readonly TimeProvider clock;
    private readonly long started;
    private readonly CancellationToken caller;
    private readonly CancellationTokenRegistration registration;
    private readonly CancellationTokenSource coordination = new();
    private readonly CancellationTokenSource collaborator = new();
    private readonly List<HoardConfigurationDiagnostic> diagnostics = [];
    private readonly List<IDisposable> resources = [];
    private readonly HashSet<string> knownOwners = new(StringComparer.Ordinal);
    private readonly HashSet<string> knownSettings = new(StringComparer.Ordinal);
    private int omitted;
    private int pending;
    private bool terminal;
    private bool completed;
    private bool disposed;
    private bool notified;
    private bool released;
    private HoardConfigurationPhase currentPhase = HoardConfigurationPhase.Sources;
    private HoardConfigurationSource currentSource;
    private string currentOwner = "configuration";
    internal Guid Correlation { get; } = Guid.NewGuid();
    internal HoardConfigurationOutcome Outcome { get; private set; } = HoardConfigurationOutcome.Failed;

    internal ConfigurationSupervisor(HoardConfigurationOptions options, CancellationToken caller)
    {
        this.options = options;
        clock = options.TimeProvider;
        started = clock.GetTimestamp();
        this.caller = caller;
        registration = caller.UnsafeRegister(_ => Fail(HoardConfigurationRule.Cancelled), null);
    }
    internal TimeSpan Remaining
    {
        get
        {
            var value = TimeSpan.FromMilliseconds(options.EvaluationTimeoutMilliseconds) - clock.GetElapsedTime(started);
            return value > TimeSpan.Zero ? value : TimeSpan.Zero;
        }
    }
    internal void Known(string owner, IEnumerable<string> settings)
    {
        lock (gate)
        {
            knownOwners.Add(owner);
            foreach (var setting in settings) { knownSettings.Add(setting); }
        }
    }
    internal void Hold(IDisposable resource)
    {
        lock (gate)
        {
            if (released) { resource.Dispose(); }
            else { resources.Add(resource); }
        }
    }
    internal HoardConfigurationSupervision Snapshot
    { get { lock (gate) { return new(pending, diagnostics.ToImmutableArray(), omitted); } } }

    private void Error(HoardConfigurationRule rule, HoardConfigurationPhase phase,
        HoardConfigurationSource source, string owner, string setting = "configuration")
    {
        var safeOwner = knownOwners.Contains(owner) ? owner : "configuration";
        var safeSetting = knownSettings.Contains(setting) ? setting : "unknown-setting";
        if (diagnostics.Count < options.MaximumDiagnostics)
        { diagnostics.Add(new(rule, phase, source, safeOwner, safeSetting, Correlation)); }
        else { omitted++; }
    }
    [DoesNotReturn]
    internal void Reject(HoardConfigurationRule rule, HoardConfigurationPhase phase,
        HoardConfigurationSource source = HoardConfigurationSource.Defaults,
        string owner = "configuration", string setting = "configuration")
    {
        lock (gate) { Error(rule, phase, source, owner, setting); }
        throw new ConfigurationFailure(rule);
    }
    internal void Check()
    {
        lock (gate)
        {
            if (caller.IsCancellationRequested) { Fail(HoardConfigurationRule.Cancelled); }
            else if (!terminal && Remaining <= TimeSpan.Zero) { Fail(HoardConfigurationRule.Timeout); }
            if (terminal)
            {
                throw new ConfigurationFailure(Outcome == HoardConfigurationOutcome.Cancelled
                ? HoardConfigurationRule.Cancelled : Outcome == HoardConfigurationOutcome.TimedOut
                    ? HoardConfigurationRule.Timeout : HoardConfigurationRule.CheckFailure);
            }
        }
    }
    internal void Fail(HoardConfigurationRule rule)
    {
        lock (gate)
        {
            if (terminal) { return; }
            terminal = true;
            Outcome = rule == HoardConfigurationRule.Cancelled ? HoardConfigurationOutcome.Cancelled
                : rule == HoardConfigurationRule.Timeout ? HoardConfigurationOutcome.TimedOut : HoardConfigurationOutcome.Failed;
            if (diagnostics.Count == 0 || rule is HoardConfigurationRule.Cancelled or HoardConfigurationRule.Timeout)
            { Error(rule, currentPhase, currentSource, currentOwner); }
            if (!notified && pending > 0)
            {
                notified = true;
                pending++;
                var phase = currentPhase;
                var source = currentSource;
                var owner = currentOwner;
                _ = Task.Run(async () =>
                {
                    try { await collaborator.CancelAsync().ConfigureAwait(false); }
                    catch (Exception)
                    { lock (gate) { Error(HoardConfigurationRule.CancellationFailure, phase, source, owner); } }
                    finally { ReleaseActivity(); }
                });
            }
            coordination.Cancel();
        }
    }
    internal async Task<T> RunAsync<T>(HoardConfigurationPhase phase, HoardConfigurationSource source,
        string owner, Func<CancellationToken, ValueTask<T>> callback)
    {
        Task<T> work;
        TimeSpan cap;
        long operationStarted;
        lock (gate)
        {
            Check();
            currentPhase = phase;
            currentSource = source;
            currentOwner = owner;
            cap = TimeSpan.FromMilliseconds(options.OperationTimeoutMilliseconds);
            if (Remaining < cap) { cap = Remaining; }
            operationStarted = clock.GetTimestamp();
            pending++;
            work = Task.Run(async () =>
            {
                try
                {
                    var result = await callback(collaborator.Token).ConfigureAwait(false);
                    Events.Add(1, new("phase", phase.ToString()), new("category", "Completed"), new("source", source.ToString()));
                    return result;
                }
                catch (Exception error)
                {
                    lock (gate)
                    {
                        var rule = terminal ? HoardConfigurationRule.LateCheckFailure
                            : error is ConfigurationFailure failure ? failure.Rule : HoardConfigurationRule.CheckFailure;
                        if (error is not ConfigurationFailure || terminal) { Error(rule, phase, source, owner); }
                        throw new ConfigurationFailure(rule);
                    }
                }
                finally { ReleaseActivity(); }
            });
            _ = work.ContinueWith(task => { _ = task.Exception; }, CancellationToken.None,
                TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
        }
        try
        {
            // Framework timers have a finite maximum even when a trusted host grants a larger budget.
            var slice = TimeSpan.FromMilliseconds(uint.MaxValue - 1);
            while (true)
            {
                var remaining = cap - clock.GetElapsedTime(operationStarted);
                if (remaining <= TimeSpan.Zero) { throw new TimeoutException(); }
                try
                {
                    var result = await work.WaitAsync(remaining < slice ? remaining : slice, clock, coordination.Token).ConfigureAwait(false);
                    if (clock.GetElapsedTime(operationStarted) >= cap) { throw new TimeoutException(); }
                    Check();
                    return result;
                }
                catch (TimeoutException) when (remaining > slice && !work.IsCompleted) { }
            }
        }
        catch (Exception error) when (error is TimeoutException or OperationCanceledException or ConfigurationFailure)
        {
            Fail(error is TimeoutException ? HoardConfigurationRule.Timeout :
                error is OperationCanceledException ? HoardConfigurationRule.Cancelled : ((ConfigurationFailure)error).Rule);
            throw new ConfigurationFailure(error is ConfigurationFailure failure ? failure.Rule :
                error is TimeoutException ? HoardConfigurationRule.Timeout : HoardConfigurationRule.Cancelled);
        }
    }
    internal bool Complete(bool success)
    {
        lock (gate)
        {
            if (success)
            {
                Check();
                terminal = true;
                Outcome = HoardConfigurationOutcome.Validated;
            }
            completed = true;
            registration.Unregister();
            ReleaseResources();
            return success;
        }
    }
    internal void Dispose()
    {
        lock (gate) { disposed = true; ReleaseResources(); }
    }
    private void ReleaseActivity()
    { lock (gate) { pending--; ReleaseResources(); } }
    private void ReleaseResources()
    {
        if (!completed || !disposed || pending != 0 || released) { return; }
        released = true;
        foreach (var resource in resources) { resource.Dispose(); }
        resources.Clear();
        collaborator.Dispose();
        coordination.Dispose();
    }
}
