using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore
{
    private int failNextWrite;
    public void InjectStorageCapacityForTest() => Interlocked.Exchange(ref failNextWrite, 1);
    public void ClearStorageCapacityForTest() => Interlocked.Exchange(ref failNextWrite, 0);

    public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutForTestAsync(bool partial) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, false, async activity =>
        {
            await EnterWriterAsync(activity);
            try
            {
                Volatile.Write(ref state, state with { Schema = 3 });
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });

    public async ValueTask<IDisposable> HoldWriterForTestAsync(CancellationToken cancellationToken = default)
    {
        if (!await writer.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken))
        { throw new TimeoutException("Synthetic writer acquisition timed out."); }
        return new WriterHold(writer);
    }

    private sealed class WriterHold(SemaphoreSlim writer) : IDisposable
    {
        private int released;
        public void Dispose() { if (Interlocked.Exchange(ref released, 1) == 0) { writer.Release(); } }
    }

    public ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationForTestAsync(CanonicalText resource, long generation) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            await EnterWriterAsync(activity);
            try
            {
                var key = new MetadataSelector.Lease(resource);
                var lease = state.Records[key] as MetadataWorkLease ?? throw new InvalidOperationException("Missing synthetic lease.");
                Volatile.Write(ref state, state with { Records = state.Records.SetItem(key, lease with { Generation = generation }) });
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MetadataId>> FillLedgerForTestAsync() =>
        Dispatch(TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30), default, MetadataPhase.Reserve, null, true, async activity =>
        {
            await EnterWriterAsync(activity);
            try
            {
                var root = state;
                var now = Now(root);
                var operations = root.Operations.ToBuilder();
                while (operations.Count < 100000)
                {
                    activity.Check();
                    var ticket = new MetadataOperationTicket(root.Epoch, new(Guid.NewGuid()), new(now), new(checked(now + 86400000)));
                    operations.Add(ticket.Id, new(ticket, 0, null, null));
                }
                Volatile.Write(ref state, root with { Operations = operations.ToImmutable(), TimeFloor = now });
                return Success(root.Epoch);
            }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MetadataId>> CorruptRecordForTestAsync(MetadataSelector selector) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            await EnterWriterAsync(activity);
            try
            {
                Volatile.Write(ref state, state with { Records = state.Records.WithPayload(selector, "{") });
                await observe("memory.persisted.changed");
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MetadataId>> MakeFutureSchemaForTestAsync() =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            await EnterWriterAsync(activity);
            try
            {
                Volatile.Write(ref state, state with { Schema = 3 });
                lock (activitiesLock) { admitted = false; }
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });
}
