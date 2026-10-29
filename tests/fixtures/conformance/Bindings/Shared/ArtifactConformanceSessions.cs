using System.Collections.Immutable;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Shared;

internal sealed class ArtifactConformanceSession : IArtifactConformanceSession
{
    private readonly IArtifactAssertionSession session;
    private readonly ConformanceRunContext context;
    private readonly ArtifactConformanceFaults faults;

    public ArtifactConformanceSession(IArtifactAssertionSession session, ConformanceRunContext context)
    {
        this.session = session;
        this.context = context;
        faults = new(session, context);
    }

    public IArtifactStore Store => session.Store;
    public IArtifactEvidenceValidator Validator => session.Validator;
    public IArtifactMaintenance Maintenance => session.Maintenance;
    public IArtifactStoreLifetime Lifetime => session.Lifetime;
    public IArtifactCoordinationAuthority Authority => session.Authority;
    public ArtifactStoreIdentity Identity => session.Identity;
    public IArtifactConformanceFaultDriver Faults => faults;

    public async ValueTask<IArtifactConformanceSession> ReopenAsync(CancellationToken cancellationToken)
    {
        var reopened = await session.ReopenAsync(cancellationToken);
        var handedOff = false;
        try
        {
            await faults.DisposeAfterSettlementAsync();
            var current = new ArtifactConformanceSession(reopened, context);
            handedOff = true;
            return current;
        }
        finally
        {
            if (!handedOff) { await reopened.DisposeAsync(); }
        }
    }

    public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
        session.ObserveCleanupAsync(cancellationToken);

    public async ValueTask DisposeAsync()
    {
        await session.DisposeAsync();
        await faults.DisposeAfterSettlementAsync();
    }
}

internal sealed class ArtifactConformanceFaults(
    IArtifactAssertionSession session, ConformanceRunContext context) : IArtifactConformanceFaultDriver
{
    private readonly SemaphoreSlim transfer = new(1, 1);
    private readonly Dictionary<ConformanceFault, Control> controls = [];
    private readonly List<BorrowedStream> borrowedStreams = [];
    private bool closed;

    public ImmutableArray<ConformanceFault> SupportedFaults =>
        ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts);
    public int WaitingAuthorityAdmissions => session.WaitingAuthorityAdmissions;
    public ArtifactInitializationObservation ObserveInitialization() => session.ObserveInitialization();
    public ValueTask<ArtifactCompetingInitializationObservation> ProbeCompetingInitializationAsync(
        ArtifactInitializationMode mode, CancellationToken cancellationToken) =>
        session.ProbeCompetingInitializationAsync(mode, cancellationToken);
    public ValueTask<IArtifactSynchronousHold> HoldSynchronousStorageAsync(CancellationToken cancellationToken) =>
        session.HoldSynchronousStorageAsync(cancellationToken);
    public Task ObserveWorkerSettlement() => session.ObserveWorkerSettlement();
    public IArtifactBorrowedStream BorrowedSource => Borrowed(ConformanceFault.SourceNonCooperation);
    public IArtifactBorrowedStream BorrowedDestination => Borrowed(ConformanceFault.SinkNonCooperation);

    public async ValueTask ArmAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        await EnterAsync(cancellationToken);
        try
        {
            if (closed || !session.Ready || !SupportedFaults.Contains(fault)
                || controls.TryGetValue(fault, out var previous) && !previous.Released)
            { throw new InvalidOperationException("BindingInvalid"); }
            Control control;
            if (fault is ConformanceFault.Capacity or ConformanceFault.CleanupFailure)
            {
                var injection = fault == ConformanceFault.Capacity
                    ? await session.InjectCapacityFailureAsync(cancellationToken)
                    : await session.InjectUnclaimedCleanupFailureAsync(cancellationToken);
                control = new(injection.WaitForEntryAsync, injection.DisposeAsync,
                    () => injection.ObservationCount);
            }
            else if (fault == ConformanceFault.NativeNonCooperation)
            {
                var hold = await session.HoldSynchronousStorageAsync(cancellationToken);
                control = new(hold.WaitForEntryAsync, async () =>
                {
                    hold.Release();
                    await session.AwaitSettlementAsync(CancellationToken.None);
                    await hold.DisposeAsync();
                }, () => hold.ObservationCount);
            }
            else if (fault is ConformanceFault.SourceNonCooperation or ConformanceFault.SinkNonCooperation)
            {
                var stream = new BorrowedStream(fault == ConformanceFault.SourceNonCooperation, context);
                borrowedStreams.Add(stream);
                control = new(stream.WaitForEntryAsync, () =>
                {
                    stream.Release();
                    return ValueTask.CompletedTask;
                }, () => stream.ObservationCount, stream);
            }
            else
            {
                var gate = new BoundaryGate(context, fault != ConformanceFault.PayloadDamage);
                var point = fault switch
                {
                    ConformanceFault.PublicationBoundary => ArtifactObservationPoint.PublicationSelected,
                    ConformanceFault.DirectVisibility => ArtifactObservationPoint.DirectVerification,
                    ConformanceFault.PayloadDamage => ArtifactObservationPoint.PayloadDamage,
                    ConformanceFault.GenerationBoundary => ArtifactObservationPoint.StageVerified,
                    ConformanceFault.ReceiptBoundary => ArtifactObservationPoint.ReceiptPersisted,
                    _ => throw new InvalidOperationException("BindingInvalid")
                };
                var registration = await session.ObserveBoundaryAsync(point, gate.ArriveAsync, cancellationToken);
                control = new(gate.WaitForEntryAsync, async () =>
                {
                    gate.Release();
                    await registration.DisposeAsync();
                }, () => gate.ObservationCount);
            }
            controls[fault] = control;
        }
        finally { transfer.Release(); }
    }

    public async ValueTask WaitForBoundaryAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        var control = await CurrentAsync(fault, cancellationToken);
        await control.Wait(cancellationToken);
    }

    public async ValueTask ReleaseAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        TaskCompletionSource? start = null;
        Task releasing;
        await EnterAsync(cancellationToken);
        try
        {
            var control = Current(fault);
            if (control.Releasing is null or { IsFaulted: true } or { IsCanceled: true })
            {
                start = new(TaskCreationOptions.RunContinuationsAsynchronously);
                control.Releasing = ReleaseCoreAsync(control, start.Task);
            }
            releasing = control.Releasing;
        }
        finally
        {
            transfer.Release();
            start?.TrySetResult();
        }
        await releasing;
    }

    private static async Task ReleaseCoreAsync(Control control, Task start)
    {
        await start;
        await control.Release();
    }

    public async ValueTask<ConformanceFaultObservation> ObserveAsync(
        ConformanceFault fault, CancellationToken cancellationToken)
    {
        var control = await CurrentAsync(fault, cancellationToken);
        var cleanup = await session.ObserveCleanupAsync(cancellationToken);
        return new(fault, "artifact." + fault, control.Count(), cleanup.State);
    }

    public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        ArtifactObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken) =>
        session.ObserveBoundaryAsync(point, observer, cancellationToken);

    public ValueTask<IArtifactFaultRegistration> InjectPublicationAcknowledgmentLossAsync(CancellationToken cancellationToken) =>
        session.InjectPublicationAcknowledgmentLossAsync(cancellationToken);

    public ValueTask<IArtifactFaultRegistration> InjectRecordWriteFailureAsync(
        int occurrence, Action beforeFailure, CancellationToken cancellationToken) =>
        session.InjectRecordWriteFailureAsync(occurrence, beforeFailure, cancellationToken);

    public ValueTask<IAsyncDisposable> ObserveHistoryCandidatesAsync(
        Action<string, string> observer, CancellationToken cancellationToken) =>
        session.ObserveHistoryCandidatesAsync(observer, cancellationToken);

    public ValueTask<IArtifactFaultRegistration> InjectHistoryCandidateFailureAsync(CancellationToken cancellationToken) =>
        session.InjectHistoryCandidateFailureAsync(cancellationToken);

    public ValueTask<IArtifactFaultRegistration> InjectObservationFailureAsync(
        ArtifactObservationPoint point, Func<ValueTask> beforeFailure, CancellationToken cancellationToken) =>
        session.InjectObservationFailureAsync(point, beforeFailure, cancellationToken);

    public async ValueTask DamagePayloadAsync(
        ArtifactStamp stamp, bool truncate, CancellationToken cancellationToken)
    {
        var control = await CurrentAsync(ConformanceFault.PayloadDamage, cancellationToken);
        if (control.Released || !session.Ready) { throw new InvalidOperationException("BindingInvalid"); }
        await session.DamagePayloadAsync(stamp, truncate, cancellationToken);
    }

    public ValueTask AwaitSettlementAsync(CancellationToken cancellationToken) =>
        session.AwaitSettlementAsync(cancellationToken);

    public ValueTask<byte[]> CapturePayloadAsync(ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken) =>
        session.CapturePayloadAsync(stamp, maximumBytes, cancellationToken);

    public ValueTask ReplacePayloadAsync(ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken) =>
        session.ReplacePayloadAsync(stamp, payload, cancellationToken);

    public ValueTask RemovePayloadAsync(ArtifactStamp stamp, CancellationToken cancellationToken) =>
        session.RemovePayloadAsync(stamp, cancellationToken);

    public ValueTask<IAsyncDisposable> RestrictPayloadAccessAsync(
        ArtifactStamp stamp, bool unavailable, CancellationToken cancellationToken) =>
        session.RestrictPayloadAccessAsync(stamp, unavailable, cancellationToken);

    public ValueTask<IAsyncDisposable> RestrictRecordWritesAsync(CancellationToken cancellationToken) =>
        session.RestrictRecordWritesAsync(cancellationToken);
    public ValueTask<IAsyncDisposable> RestrictStorageCleanupAsync(ArtifactStorageArea area, CancellationToken cancellationToken) =>
        session.RestrictStorageCleanupAsync(area, cancellationToken);
    public ValueTask<ArtifactStorageObservation> ObserveStorageAsync(CancellationToken cancellationToken) =>
        session.ObserveStorageAsync(cancellationToken);

    internal async ValueTask DisposeAfterSettlementAsync()
    {
        await EnterAsync(CancellationToken.None);
        try
        {
            closed = true;
            foreach (var stream in borrowedStreams) { await stream.DisposeAsync(); }
        }
        finally { transfer.Release(); }
    }

    private async ValueTask EnterAsync(CancellationToken cancellationToken)
    {
        if (!await transfer.WaitAsync(context.ControlBudget, cancellationToken))
        { throw new InvalidOperationException("CleanupIncomplete"); }
    }

    private Control Current(ConformanceFault fault) =>
        controls.TryGetValue(fault, out var control) ? control : throw new InvalidOperationException("BindingInvalid");

    private async ValueTask<Control> CurrentAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        await EnterAsync(cancellationToken);
        try { return Current(fault); }
        finally { transfer.Release(); }
    }

    private IArtifactBorrowedStream Borrowed(ConformanceFault fault)
    {
        if (!transfer.Wait(context.ControlBudget)) { throw new InvalidOperationException("CleanupIncomplete"); }
        try { return Current(fault).Borrowed ?? throw new InvalidOperationException("BindingInvalid"); }
        finally { transfer.Release(); }
    }

    private sealed class Control(
        Func<CancellationToken, ValueTask> wait, Func<ValueTask> release, Func<long> count,
        IArtifactBorrowedStream? borrowed = null)
    {
        public Func<CancellationToken, ValueTask> Wait { get; } = wait;
        public Func<ValueTask> Release { get; } = release;
        public Func<long> Count { get; } = count;
        public IArtifactBorrowedStream? Borrowed { get; } = borrowed;
        public Task? Releasing { get; set; }
        public bool Released => Releasing is { IsCompletedSuccessfully: true };
    }

    private sealed class BoundaryGate(ConformanceRunContext context, bool hold)
    {
        private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private long count;
        public long ObservationCount => Interlocked.Read(ref count);
        public async ValueTask ArriveAsync()
        {
            Interlocked.Increment(ref count);
            entered.TrySetResult();
            if (hold) { await released.Task.WaitAsync(context.BarrierBudget); }
        }
        public ValueTask WaitForEntryAsync(CancellationToken cancellationToken) =>
            new(entered.Task.WaitAsync(context.ControlBudget, cancellationToken));
        public void Release() => released.TrySetResult();
    }

    private sealed class BorrowedStream(bool source, ConformanceRunContext context)
        : MemoryStream, IArtifactBorrowedStream
    {
        private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private long count;
        public Stream Stream => this;
        public bool WasDisposed { get; private set; }
        public long ObservationCount => Interlocked.Read(ref count);
        public ValueTask WaitForEntryAsync(CancellationToken cancellationToken) =>
            new(entered.Task.WaitAsync(context.ControlBudget, cancellationToken));
        public void Release() => released.TrySetResult();
        private async Task HoldAsync()
        {
            Interlocked.Increment(ref count);
            entered.TrySetResult();
            await released.Task;
        }
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            ObjectDisposedException.ThrowIf(WasDisposed, this);
            if (!source) { throw new InvalidOperationException("BindingInvalid"); }
            await HoldAsync();
            return await base.ReadAsync(buffer, CancellationToken.None);
        }
        public override async ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
        {
            ObjectDisposedException.ThrowIf(WasDisposed, this);
            if (source) { throw new InvalidOperationException("BindingInvalid"); }
            await HoldAsync();
            await base.WriteAsync(buffer, CancellationToken.None);
        }
        protected override void Dispose(bool disposing)
        {
            WasDisposed = true;
            base.Dispose(disposing);
        }
    }
}
