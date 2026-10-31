using System.Collections.Concurrent;
using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Memory;

internal sealed partial class MemoryMetadataFaults(
    ConformanceRunContext context, Func<bool> isClosing) : IMetadataConformanceFaultDriver
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> observers = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<ConformanceFault, FaultGate> gates = new();
    private readonly SemaphoreSlim arming = new(1, 1);
    private MemoryMetadataStore? attached;
    private long boundaries;
    private long internalFailures;
    private long incompleteCleanups;
    private MemoryMetadataStore Store => attached ?? throw new InvalidOperationException("BindingInvalid");
    public ImmutableArray<ConformanceFault> SupportedFaults { get; } =
        ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata);
    public MetadataFaultCounters Counters => new(Interlocked.Read(ref boundaries),
        Interlocked.Read(ref internalFailures), Interlocked.Read(ref incompleteCleanups));

    public void Attach(MemoryMetadataStore store)
    {
        if (Interlocked.CompareExchange(ref attached, store, null) is not null)
        { throw new InvalidOperationException("BindingInvalid"); }
    }

    public ValueTask OnBoundaryAsync(string point)
    {
        Interlocked.Increment(ref boundaries);
        return observers.TryGetValue(point, out var observer) ? observer() : ValueTask.CompletedTask;
    }

    public void OnDiagnostic(string code)
    {
        switch (code)
        {
            case "metadata.internal_failure": Interlocked.Increment(ref internalFailures); break;
            case "metadata.cleanup_incomplete": Interlocked.Increment(ref incompleteCleanups); break;
            default: throw new InvalidOperationException("UnknownDiagnostic");
        }
    }

    public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(
        MetadataObservationPoint point, Func<ValueTask> observer, CancellationToken cancellationToken) =>
        RegisterAsync(point switch
        {
            MetadataObservationPoint.BeforeCommitDecision => "M0",
            MetadataObservationPoint.AfterCommitDecision => "M1",
            MetadataObservationPoint.MutationApplied => "mutation.applied",
            MetadataObservationPoint.CorruptionCaptured => "corruption.captured",
            MetadataObservationPoint.PayloadChanged => "memory.persisted.changed",
            MetadataObservationPoint.ReadItem => "read.item",
            MetadataObservationPoint.BeforeReconciliationDecision => "reconcile.before_decision",
            MetadataObservationPoint.BeforeSchemaUpgrade or MetadataObservationPoint.SchemaCandidatePrepared => "memory.upgrade.before_decision",
            _ => throw new ArgumentException("BindingInvalid")
        }, observer, cancellationToken);

    private ValueTask<IAsyncDisposable> RegisterAsync(
        string point, Func<ValueTask> observer, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(observer);
        if (isClosing() || !observers.TryAdd(point, observer)) { throw new InvalidOperationException("BindingInvalid"); }
        return ValueTask.FromResult<IAsyncDisposable>(new Registration(observers, point, observer));
    }

    public async ValueTask ArmAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        Require(fault);
        if (!await arming.WaitAsync(context.ControlBudget, cancellationToken))
        { throw new InvalidOperationException("BindingInvalid"); }
        try
        {
            if (isClosing() || gates.TryGetValue(fault, out var previous) && !previous.Released)
            { throw new InvalidOperationException("BindingInvalid"); }
            var control = new FaultGate(fault == ConformanceFault.CleanupFailure
                ? TimeSpan.FromSeconds(60) : context.BarrierBudget,
                fault is not (ConformanceFault.Capacity or ConformanceFault.PersistedCorruption));
            if (fault == ConformanceFault.WriterContention)
            {
                control.Writer = await HoldWriterAsync(cancellationToken);
                control.MarkWriterAcquired();
            }
            else
            {
                var point = fault switch
                {
                    ConformanceFault.IndependentSnapshot => "read.item",
                    ConformanceFault.CommitAcknowledgement => "M1",
                    ConformanceFault.PersistedCorruption => "memory.persisted.changed",
                    ConformanceFault.Capacity => "memory.storage_capacity",
                    ConformanceFault.SchemaState => "schema.inspect",
                    ConformanceFault.LeaseBoundary or ConformanceFault.NativeNonCooperation
                        or ConformanceFault.CleanupFailure => "M0",
                    _ => throw new ArgumentException("BindingInvalid")
                };
                control.Registration = await RegisterAsync(point, control.EnterAsync, cancellationToken);
            }
            gates[fault] = control;
            if (fault == ConformanceFault.Capacity) { Store.InjectStorageCapacityForTest(); }
        }
        finally { arming.Release(); }
    }

    public ValueTask WaitForBoundaryAsync(ConformanceFault fault, CancellationToken cancellationToken) =>
        new(Get(fault).Entered.WaitAsync(context.ControlBudget, cancellationToken));

    public async ValueTask ReleaseAsync(ConformanceFault fault, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var control = Get(fault);
        if (fault == ConformanceFault.Capacity) { Store.ClearStorageCapacityForTest(); }
        await control.ReleaseAsync();
    }

    public async ValueTask<ConformanceFaultObservation> ObserveAsync(
        ConformanceFault fault, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var observation = new ConformanceFaultObservation(fault, "memory." + fault, Get(fault).Arrivals,
            isClosing() ? ConformanceOwnershipState.Settling : ConformanceOwnershipState.Active);
        await context.Evidence.ObserveAsync(observation, cancellationToken);
        return observation;
    }

    private void Require(ConformanceFault fault)
    {
        if (!SupportedFaults.Contains(fault)) { throw new ArgumentException("BindingInvalid"); }
    }

    private FaultGate Get(ConformanceFault fault)
    {
        Require(fault);
        return gates.TryGetValue(fault, out var value) ? value : throw new InvalidOperationException("BindingInvalid");
    }

    public async ValueTask DisposeControlsAsync()
    {
        foreach (var control in gates.Values) { await control.ReleaseAsync(); }
    }

    public ValueTask AwaitSettlementAsync(CancellationToken cancellationToken) =>
        new(Store.ObserveWorkSettlementForTest().WaitAsync(context.ControlBudget, cancellationToken));

    public ValueTask<ConformanceStateFingerprint> ObserveStateAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult(new ConformanceStateFingerprint(Store.CaptureLogicalImage().ComputeFingerprint(cancellationToken)));
    }

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotAsync(
        MetadataReadGroup request, CancellationToken cancellationToken) =>
        Store.ReadIndependentSnapshotForTestAsync(request, cancellationToken);

    public async ValueTask<IAsyncDisposable> HoldWriterAsync(CancellationToken cancellationToken)
    {
        if (isClosing()) { throw new InvalidOperationException("BindingInvalid"); }
        return new WriterHold(await Store.HoldWriterForTestAsync(cancellationToken));
    }

    public ValueTask<MetadataResult<MetadataId>> FillLedgerAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store.FillLedgerForTestAsync();
    }

    public ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(
        MetadataSelector selector, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store.CorruptRecordForTestAsync(selector);
    }

    public ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationAsync(
        CanonicalText resource, long generation, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store.SetLeaseGenerationForTestAsync(resource, generation);
    }

    public ValueTask<MetadataResult<MetadataId>> SetFutureSchemaAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store.MakeFutureSchemaForTestAsync();
    }

    public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutAsync(bool partial, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Store.CreateUnrecognizedLayoutForTestAsync(partial);
    }

    public ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult(Store.AuthorizeLogicalUpgrade());
    }

    private sealed class Registration(
        ConcurrentDictionary<string, Func<ValueTask>> observers, string key, Func<ValueTask> observer) : IAsyncDisposable
    {
        private int disposed;
        public ValueTask DisposeAsync()
        {
            if (Interlocked.Exchange(ref disposed, 1) == 0
                && !observers.TryRemove(new KeyValuePair<string, Func<ValueTask>>(key, observer)))
            { throw new InvalidOperationException("BindingInvalid"); }
            return ValueTask.CompletedTask;
        }
    }

    private sealed class WriterHold(IDisposable owned) : IAsyncDisposable
    {
        private IDisposable? writer = owned;
        public ValueTask DisposeAsync()
        {
            Interlocked.Exchange(ref writer, null)?.Dispose();
            return ValueTask.CompletedTask;
        }
    }

    private sealed class FaultGate(TimeSpan holdBudget, bool hold)
    {
        private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private long arrivals;
        public IAsyncDisposable? Registration { get; set; }
        public IAsyncDisposable? Writer { get; set; }
        public Task Entered => entered.Task;
        public bool Released => released.Task.IsCompleted;
        public long Arrivals => Interlocked.Read(ref arrivals);

        public void MarkWriterAcquired()
        {
            Interlocked.Increment(ref arrivals);
            entered.TrySetResult();
        }

        public async ValueTask EnterAsync()
        {
            if (Interlocked.CompareExchange(ref arrivals, 1, 0) != 0) { return; }
            entered.TrySetResult();
            if (hold) { await released.Task.WaitAsync(holdBudget); }
        }

        public async ValueTask ReleaseAsync()
        {
            released.TrySetResult();
            try
            {
                if (Registration is not null) { await Registration.DisposeAsync(); }
            }
            finally
            {
                if (Writer is not null) { await Writer.DisposeAsync(); }
            }
        }
    }
}
