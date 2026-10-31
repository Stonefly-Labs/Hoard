using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Shared;

internal sealed class MetadataCorruptionOwnership(TimeSpan controlBudget)
{
    private readonly object gate = new();
    private readonly Dictionary<Target, Owner> owners = [];
    private bool closing;

    public bool IsClosing
    {
        get { lock (gate) { return closing; } }
    }

    public void BeginClosure()
    {
        lock (gate)
        {
            if (owners.Count != 0) { throw new InvalidOperationException("FaultControl.CorruptionOwned"); }
            closing = true;
        }
    }

    public async ValueTask RestoreAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        Owner[] pending;
        lock (gate) { pending = [.. owners.Values]; }
        foreach (var owner in pending)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (Volatile.Read(ref owner.Applying) != 0 || owner.Scope is not { } scope)
            { throw new InvalidOperationException("FaultControl.CorruptionOwned"); }
            await scope.DisposeAsync();
        }
    }

    public async ValueTask<IMetadataCorruptionScope> ApplyAsync<T>(
        MetadataCorruptionRequest request, Func<ValueTask<T>> read, Func<T, T> damage,
        Func<T, T, Action, ValueTask> replace, Func<T, ValueTask> restore,
        Func<T, ConformanceStateFingerprint> fingerprint, Func<ValueTask> captured,
        Func<CancellationToken, ValueTask> settle, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var target = request switch
        {
            MetadataCorruptionRequest.Record record => new Target(record.Selector, null, null),
            MetadataCorruptionRequest.Operation operation => new Target(null, operation.Ticket.Epoch.Value, operation.Ticket.Id.Value),
            _ => throw new ArgumentException("BindingInvalid")
        };
        var owner = new Owner();
        lock (gate)
        {
            if (closing) { throw new InvalidOperationException("FaultControl.Closing"); }
            if (!owners.TryAdd(target, owner)) { throw new InvalidOperationException("FaultControl.CorruptionOwned"); }
        }
        Scope? scope = null;
        var submitted = false;
        var applied = 0;
        var handedOff = false;
        try
        {
            var original = await read();
            var damaged = damage(original);
            var originalFingerprint = fingerprint(original);
            scope = new(originalFingerprint, async () => fingerprint(await read()),
                async () =>
                {
                    if (!submitted) { return; }
                    await settle(CancellationToken.None);
                    if (Volatile.Read(ref applied) == 0) { return; }
                    await restore(original);
                    await settle(CancellationToken.None);
                    if (fingerprint(await read()) != originalFingerprint)
                    { throw new InvalidOperationException("FaultControl.RestorationMismatch"); }
                }, () => Release(target, owner), controlBudget);
            owner.Scope = scope;
            await captured();
            cancellationToken.ThrowIfCancellationRequested();
            submitted = true;
            await replace(original, damaged, () => Volatile.Write(ref applied, 1));
            cancellationToken.ThrowIfCancellationRequested();
            handedOff = true;
            return scope;
        }
        finally
        {
            try
            {
                if (!handedOff)
                {
                    if (scope is not null) { await scope.DisposeAsync(); }
                    else { Release(target, owner); }
                }
            }
            finally { Volatile.Write(ref owner.Applying, 0); }
        }
    }

    private void Release(Target target, Owner owner)
    {
        lock (gate)
        {
            if (owners.TryGetValue(target, out var current) && ReferenceEquals(current, owner))
            { owners.Remove(target); }
        }
    }

    private sealed record Target(MetadataSelector? Record, Guid? Epoch, Guid? Operation);

    private sealed class Owner
    {
        public int Applying = 1;
        public Scope? Scope;
    }

    private sealed class Scope(ConformanceStateFingerprint original, Func<ValueTask<ConformanceStateFingerprint>> read,
        Func<ValueTask> restore, Action release, TimeSpan controlBudget) : IMetadataCorruptionScope
    {
        private readonly SemaphoreSlim restoring = new(1, 1);
        private bool restored;
        public ConformanceStateFingerprint Original { get; } = original;

        public ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return read();
        }

        public async ValueTask DisposeAsync()
        {
            if (!await restoring.WaitAsync(controlBudget))
            { throw new InvalidOperationException("FaultControl.CorruptionOwned"); }
            try
            {
                if (restored) { return; }
                await restore();
                restored = true;
                release();
            }
            finally { restoring.Release(); }
        }
    }
}
