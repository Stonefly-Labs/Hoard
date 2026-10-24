using System.Collections.Concurrent;
using System.Diagnostics;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Local;

public static class LocalArtifactAssertionSessions
{
    public static async ValueTask<IArtifactAssertionSession> CreateAsync(
        ConformanceRunContext context, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(context);
        var resource = await context.Resources.AllocateDirectoryAsync(cancellationToken);
        var ownership = new Ownership(context, resource);
        var admitted = false;
        try
        {
            var session = ownership.CreateSession();
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

    private sealed class Ownership
    {
        public Ownership(ConformanceRunContext context, ConformanceOwnedDirectory resource)
        {
            Context = context;
            Resource = resource;
            Identity = new("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
            Authority = new(Identity, context.Clock);
        }

        public object Gate { get; } = new();
        public ConformanceRunContext Context { get; }
        public ConformanceOwnedDirectory Resource { get; }
        public ArtifactStoreIdentity Identity { get; }
        public ArtifactCoordinationAuthority Authority { get; }
        public Session? Current { get; set; }
        public bool Closing { get; private set; }
        public Task? Transition { get; private set; }
        public ConcurrentQueue<Exception> ObserverFailures { get; } = new();
        private readonly List<Session> sessions = [];
        private readonly TaskCompletionSource settlement = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private Task? disposal;
        private Task<ConformanceCleanupObservation>? cleanup;

        public Session CreateSession()
        {
            var session = new Session(this);
            sessions.Add(session);
            return session;
        }

        public ValueTask<IArtifactAssertionSession> ReopenAsync(Session original, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            Task<IArtifactAssertionSession> task;
            lock (Gate)
            {
                if (Closing || !ReferenceEquals(Current, original) || Transition is { IsCompleted: false })
                { throw new InvalidOperationException("BindingInvalid"); }
                task = ReopenCoreAsync(start.Task, cancellationToken);
                Transition = task;
            }
            start.SetResult();
            return new(task);
        }

        private async Task<IArtifactAssertionSession> ReopenCoreAsync(Task start, CancellationToken cancellationToken)
        {
            await start;
            await CloseStoresAsync(final: false);
            cancellationToken.ThrowIfCancellationRequested();
            Authority.ReopenAdmissionsForQualification();
            var replacement = CreateSession();
            var admitted = false;
            try
            {
                await replacement.InitializeAsync(ArtifactInitializationMode.ReopenCompatible, cancellationToken);
                lock (Gate) { Current = replacement; }
                admitted = true;
                return replacement;
            }
            finally
            {
                if (!admitted) { await CloseStoresAsync(final: false); }
            }
        }

        public ValueTask DisposeAsync(Session? requested = null)
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
            var authority = Authority.CloseAdmissionsAndObserveSettlementForQualificationAsync();
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
                await authority.WaitAsync(Remaining(started));
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

    private sealed class Session : IArtifactAssertionSession
    {
        private readonly Ownership ownership;
        private readonly LocalArtifactStore store;
        private readonly LocalFaultControls controls = new();
        private readonly Dictionary<ArtifactObservationPoint, Registration> observations = [];
        private readonly object stopGate = new();
        private Task<ArtifactResult<ArtifactShutdown>>? stopping;

        public Session(Ownership ownership)
        {
            this.ownership = ownership;
            store = new(Path.Combine(ownership.Resource.DirectoryPath, "store"), ownership.Context.Clock, controls);
        }

        public IArtifactStore Store => store;
        public IArtifactEvidenceValidator Validator => store;
        public IArtifactMaintenance Maintenance => store;
        public IArtifactStoreLifetime Lifetime => store;
        public IArtifactCoordinationAuthority Authority => ownership.Authority;
        public ArtifactStoreIdentity Identity => ownership.Identity;
        public bool Ready
        {
            get
            {
                lock (ownership.Gate)
                {
                    return ReferenceEquals(ownership.Current, this) && !ownership.Closing
                        && ownership.Transition is not { IsCompleted: false }
                        && ownership.ObserverFailures.IsEmpty && store.Ready;
                }
            }
        }

        public async Task InitializeAsync(ArtifactInitializationMode mode, CancellationToken cancellationToken)
        {
            var result = await store.InitializeAsync(new(mode, Identity, Authority), new(), cancellationToken);
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
            return await store.StopAsync(new(budget), CancellationToken.None);
        }

        public ValueTask AwaitSettlementAsync(CancellationToken cancellationToken) =>
            new(ObserveWorkerSettlement().WaitAsync(ownership.Context.ControlBudget, cancellationToken));

        public Task ObserveWorkerSettlement() => store.WhenIdleForQualificationAsync();

        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
            ownership.ObserveCleanupAsync(cancellationToken);

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
                controls.SetObserver(boundary, async () =>
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
                foreach (var registration in observations.Values) { controls.RemoveObserver(registration.Boundary); }
                observations.Clear();
            }
        }

        private static string Boundary(ArtifactObservationPoint point) => point switch
        {
            ArtifactObservationPoint.StagePrefix => "stage.prefix",
            ArtifactObservationPoint.StageVerified => "stage.verified",
            ArtifactObservationPoint.PublicationAdmitted => "publish.admitted",
            ArtifactObservationPoint.BeforePublicationDecision => "publish.before-decision",
            ArtifactObservationPoint.PublicationSelected => "publish.decided",
            ArtifactObservationPoint.ReceiptPersisted => "publish.receipted",
            ArtifactObservationPoint.ReadOpened => "read.opened",
            ArtifactObservationPoint.ReadCopy => "read.copy",
            ArtifactObservationPoint.DeleteRemoved => "delete.removed",
            ArtifactObservationPoint.DeleteReclaimed => "delete.reclaimed",
            ArtifactObservationPoint.CleanupCandidate => "cleanup.candidate",
            ArtifactObservationPoint.TransferQueued => "transfer.queued",
            ArtifactObservationPoint.BeforeReconciliation => "reconcile.before-resolution",
            ArtifactObservationPoint.ReconciliationVerified => "reconcile.verified",
            ArtifactObservationPoint.OperationReleased => "operation.released",
            ArtifactObservationPoint.OperationCompleted => "operation.completed",
            ArtifactObservationPoint.OperationReclaim => "operation.reclaim",
            _ => throw new ArgumentException("BindingInvalid")
        };

        private sealed class Registration(Session session, ArtifactObservationPoint point, string boundary) : IAsyncDisposable
        {
            public string Boundary { get; } = boundary;
            public ValueTask DisposeAsync()
            {
                lock (session.ownership.Gate)
                {
                    if (session.observations.TryGetValue(point, out var current) && ReferenceEquals(current, this))
                    {
                        session.controls.RemoveObserver(Boundary);
                        session.observations.Remove(point);
                    }
                }
                return ValueTask.CompletedTask;
            }
        }
    }
}
