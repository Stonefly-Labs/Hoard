using System.Collections.Concurrent;
using System.Diagnostics;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Shared;

internal enum ArtifactAssertionRestart { Compatible, FreshEpoch }

internal sealed record ArtifactAssertionGeneration(
    ArtifactStoreIdentity Identity, ArtifactCoordinationAuthority Authority, string DirectoryPath, ArtifactLimits Limits);

internal sealed class ArtifactAssertionOwnership
{
    private readonly string providerId;
    private readonly Guid instanceId = Guid.NewGuid();
    private readonly ArtifactAssertionRestart restart;
    private readonly ArtifactAssertionOptions options;
    private readonly Func<ArtifactAssertionOwnership, ArtifactAssertionGeneration, ArtifactAssertionSession> create;
    private readonly List<ArtifactAssertionSession> sessions = [];
    private readonly List<ArtifactAssertionGeneration> generations = [];
    private readonly TaskCompletionSource settlement = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private Task? disposal;
    private Task<ConformanceCleanupObservation>? cleanup;

    private ArtifactAssertionOwnership(ConformanceRunContext context, ConformanceOwnedDirectory resource,
        string providerId, ArtifactAssertionRestart restart, ArtifactAssertionOptions options,
        Func<ArtifactAssertionOwnership, ArtifactAssertionGeneration, ArtifactAssertionSession> create)
    {
        Context = context;
        Resource = resource;
        this.providerId = providerId;
        this.restart = restart;
        this.options = options;
        this.create = create;
    }

    public object Gate { get; } = new();
    public ConformanceRunContext Context { get; }
    public ConformanceOwnedDirectory Resource { get; }
    public ArtifactAssertionSession? Current { get; private set; }
    public bool Closing { get; private set; }
    public Task? Transition { get; private set; }
    public ConcurrentQueue<Exception> ObserverFailures { get; } = new();

    public static async ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, string providerId, ArtifactAssertionRestart restart, ArtifactAssertionOptions options,
        Func<ArtifactAssertionOwnership, ArtifactAssertionGeneration, ArtifactAssertionSession> create,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(options);
        var resource = await context.Resources.AllocateDirectoryAsync(cancellationToken);
        var ownership = new ArtifactAssertionOwnership(context, resource, providerId, restart, options, create);
        var admitted = false;
        try
        {
            var session = ownership.CreateSession(ownership.CreateGeneration("store"));
            ownership.Current = session;
            await session.InitializeAsync(ArtifactInitializationMode.CreateEmpty, cancellationToken);
            admitted = true;
            return session;
        }
        finally
        {
            if (!admitted) { await ownership.DisposeAsync(); }
        }
    }

    private ArtifactAssertionGeneration CreateGeneration(string child)
    {
        var identity = new ArtifactStoreIdentity(providerId, instanceId, Guid.NewGuid());
        var generation = new ArtifactAssertionGeneration(identity,
            new(identity, Context.Clock, options.References is null ? null : QueryReferencesAsync),
            Path.Combine(Resource.DirectoryPath, child), options.Limits);
        generations.Add(generation);
        return generation;
    }

    private async ValueTask<ArtifactReferenceDecision> QueryReferencesAsync(
        ArtifactStamp stamp, CancellationToken cancellationToken)
    {
        var query = options.References ?? throw new InvalidOperationException("BindingInvalid");
        var observation = await query(stamp, cancellationToken)
            ?? throw new InvalidOperationException("BindingInvalid");
        return new(observation.Available, observation.LiveReferences, observation.Revision);
    }

    private ArtifactAssertionSession CreateSession(ArtifactAssertionGeneration generation)
    {
        var session = create(this, generation);
        sessions.Add(session);
        return session;
    }

    public ValueTask<IArtifactAssertionSession> ReopenAsync(
        ArtifactAssertionSession original, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task<IArtifactAssertionSession> task;
        lock (Gate)
        {
            if (Closing || !ReferenceEquals(Current, original) || Transition is { IsCompleted: false })
            { throw new InvalidOperationException("BindingInvalid"); }
            task = ReopenCoreAsync(original, start.Task, cancellationToken);
            Transition = task;
        }
        start.SetResult();
        return new(task);
    }

    private async Task<IArtifactAssertionSession> ReopenCoreAsync(
        ArtifactAssertionSession original, Task start, CancellationToken cancellationToken)
    {
        await start;
        await CloseStoresAsync(final: false);
        cancellationToken.ThrowIfCancellationRequested();
        var admitted = false;
        try
        {
            ArtifactAssertionGeneration generation;
            ArtifactInitializationMode mode;
            if (restart == ArtifactAssertionRestart.Compatible)
            {
                generation = original.Generation;
                generation.Authority.ReopenAdmissionsForQualification();
                mode = ArtifactInitializationMode.ReopenCompatible;
            }
            else
            {
                generation = CreateGeneration("epoch-" + Guid.NewGuid().ToString("N"));
                mode = ArtifactInitializationMode.CreateEmpty;
            }
            var replacement = CreateSession(generation);
            await replacement.InitializeAsync(mode, cancellationToken);
            lock (Gate) { Current = replacement; }
            admitted = true;
            return replacement;
        }
        finally
        {
            if (!admitted) { await CloseStoresAsync(final: false); }
        }
    }

    public ValueTask DisposeAsync(ArtifactAssertionSession? requested = null)
    {
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task task;
        lock (Gate)
        {
            if (requested is not null && !ReferenceEquals(Current, requested)) { return ValueTask.CompletedTask; }
            if (disposal is { IsCompleted: false } or { IsCompletedSuccessfully: true }) { return new(disposal); }
            if (Transition is { IsCompleted: false }) { throw new InvalidOperationException("CleanupIncomplete"); }
            Closing = true;
            disposal = task = DisposeCoreAsync(start.Task);
            Transition = task;
        }
        start.SetResult();
        return new(task);
    }

    private async Task DisposeCoreAsync(Task start)
    {
        await start;
        var started = Stopwatch.GetTimestamp();
        Task<ConformanceCleanupObservation>? pending;
        lock (Gate) { pending = cleanup is { IsCompleted: false } ? cleanup : null; }
        var observation = pending ?? Context.Resources.ReleaseAsync(
            Resource, settlement.Task, CancellationToken.None).AsTask();
        lock (Gate) { cleanup = observation; }
        try
        {
            await CloseStoresAsync(final: true);
            var observed = await observation.WaitAsync(Remaining(started), CancellationToken.None);
            if (observed.State != ConformanceOwnershipState.Settling)
            { throw new InvalidOperationException("CleanupIncomplete"); }
        }
        catch (TimeoutException error) { throw new InvalidOperationException("CleanupIncomplete", error); }
    }

    private async Task CloseStoresAsync(bool final)
    {
        var started = Stopwatch.GetTimestamp();
        var authorities = generations.Select(generation =>
            generation.Authority.CloseAdmissionsAndObserveSettlementForQualificationAsync()).ToArray();
        try
        {
            foreach (var session in sessions)
            {
                var result = await session.StopAsync(Remaining(started)).WaitAsync(Remaining(started));
                if (result is not ArtifactResult<ArtifactShutdown>.Success { Value.State: ArtifactCleanupState.Released })
                { throw new InvalidOperationException("CleanupIncomplete"); }
                await session.ObserveWorkerSettlement().WaitAsync(Remaining(started));
                session.RemoveObservations();
            }
            await Task.WhenAll(authorities).WaitAsync(Remaining(started));
            if (final)
            {
                if (ObserverFailures.IsEmpty) { settlement.TrySetResult(); }
                else { settlement.TrySetException(ObserverFailures.ToArray()); }
            }
        }
        catch (TimeoutException error) { throw new InvalidOperationException("CleanupIncomplete", error); }
    }

    private TimeSpan Remaining(long started)
    {
        var remaining = Context.CleanupBudget - Stopwatch.GetElapsedTime(started);
        if (remaining < TimeSpan.FromMilliseconds(1)) { throw new InvalidOperationException("CleanupIncomplete"); }
        return remaining;
    }

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (Gate)
        {
            if (cleanup is { IsCompleted: true }) { return new(cleanup); }
            return ValueTask.FromResult(new ConformanceCleanupObservation(
                Closing ? ConformanceOwnershipState.Settling : ConformanceOwnershipState.Active,
                [Resource.ResourceId]));
        }
    }
}

internal abstract class ArtifactAssertionSession : IArtifactAssertionSession
{
    private readonly ArtifactAssertionOwnership ownership;
    private readonly Dictionary<ArtifactObservationPoint, Registration> observations = [];
    private readonly object stopGate = new();
    private Task<ArtifactResult<ArtifactShutdown>>? stopping;

    protected ArtifactAssertionSession(
        ArtifactAssertionOwnership ownership, ArtifactAssertionGeneration generation)
    {
        this.ownership = ownership;
        Generation = generation;
    }

    public ArtifactAssertionGeneration Generation { get; }
    public abstract IArtifactStore Store { get; }
    public abstract IArtifactEvidenceValidator Validator { get; }
    public abstract IArtifactMaintenance Maintenance { get; }
    public abstract IArtifactStoreLifetime Lifetime { get; }
    protected abstract bool ProviderReady { get; }
    public IArtifactCoordinationAuthority Authority => Generation.Authority;
    public ArtifactStoreIdentity Identity => Generation.Identity;
    public bool Ready
    {
        get
        {
            lock (ownership.Gate)
            {
                return ReferenceEquals(ownership.Current, this) && !ownership.Closing
                    && ownership.Transition is not { IsCompleted: false }
                    && ownership.ObserverFailures.IsEmpty && ProviderReady;
            }
        }
    }

    public async Task InitializeAsync(ArtifactInitializationMode mode, CancellationToken cancellationToken)
    {
        var result = await Lifetime.InitializeAsync(new(mode, Identity, Authority, Generation.Limits), new(), cancellationToken);
        if (result is not ArtifactResult<ArtifactAdmission>.Success)
        {
            cancellationToken.ThrowIfCancellationRequested();
            throw new InvalidOperationException("BindingInvalid");
        }
    }

    public ValueTask<IArtifactAssertionSession> ReopenAsync(CancellationToken cancellationToken) =>
        ownership.ReopenAsync(this, cancellationToken);

    public ValueTask DisposeAsync() => ownership.DisposeAsync(this);

    public Task<ArtifactResult<ArtifactShutdown>> StopAsync(TimeSpan budget)
    {
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task<ArtifactResult<ArtifactShutdown>> task;
        lock (stopGate)
        {
            if (stopping is { IsCompleted: false }) { return stopping; }
            stopping = task = StopCoreAsync(start.Task, budget);
        }
        start.SetResult();
        return task;
    }

    private async Task<ArtifactResult<ArtifactShutdown>> StopCoreAsync(Task start, TimeSpan budget)
    {
        await start;
        return await Lifetime.StopAsync(new(budget), CancellationToken.None);
    }

    public ValueTask AwaitSettlementAsync(CancellationToken cancellationToken) =>
        new(ObserveWorkerSettlement().WaitAsync(ownership.Context.ControlBudget, cancellationToken));

    public abstract Task ObserveWorkerSettlement();

    protected abstract ValueTask<ArtifactResult<long>> DamageProviderPayloadAsync(
        ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken);

    public ValueTask DamagePayloadAsync(ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        cancellationToken.ThrowIfCancellationRequested();
        lock (ownership.Gate)
        {
            if (!ReferenceEquals(ownership.Current, this) || ownership.Closing
                || ownership.Transition is { IsCompleted: false })
            { throw new InvalidOperationException("BindingInvalid"); }
            return DamageCoreAsync(stamp, truncate, cancellationToken);
        }
    }

    private async ValueTask DamageCoreAsync(ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken)
    {
        var result = await DamageProviderPayloadAsync(stamp, truncate, cancellationToken);
        if (result is not ArtifactResult<long>.Success)
        {
            cancellationToken.ThrowIfCancellationRequested();
            throw new InvalidOperationException("BindingInvalid");
        }
    }

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
        ownership.ObserveCleanupAsync(cancellationToken);

    protected abstract string Boundary(ArtifactObservationPoint point);
    protected abstract void SetObserver(string boundary, Func<ValueTask> observer);
    protected abstract void RemoveObserver(string boundary);

    public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        ArtifactObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(observer);
        var boundary = Boundary(point);
        lock (ownership.Gate)
        {
            if (!ReferenceEquals(ownership.Current, this) || ownership.Closing
                || ownership.Transition is { IsCompleted: false } || observations.ContainsKey(point))
            { throw new InvalidOperationException("BindingInvalid"); }
            var registration = new Registration(this, point, boundary);
            SetObserver(boundary, async () =>
            {
                try { await observer(); }
                catch (Exception error)
                {
                    ownership.ObserverFailures.Enqueue(error);
                    throw;
                }
            });
            observations.Add(point, registration);
            return ValueTask.FromResult<IAsyncDisposable>(registration);
        }
    }

    public void RemoveObservations()
    {
        lock (ownership.Gate)
        {
            foreach (var registration in observations.Values) { RemoveObserver(registration.Boundary); }
            observations.Clear();
        }
    }

    private sealed class Registration(
        ArtifactAssertionSession session, ArtifactObservationPoint point, string boundary) : IAsyncDisposable
    {
        public string Boundary { get; } = boundary;
        public ValueTask DisposeAsync()
        {
            lock (session.ownership.Gate)
            {
                if (session.observations.TryGetValue(point, out var current) && ReferenceEquals(current, this))
                {
                    session.RemoveObserver(Boundary);
                    session.observations.Remove(point);
                }
            }
            return ValueTask.CompletedTask;
        }
    }
}
