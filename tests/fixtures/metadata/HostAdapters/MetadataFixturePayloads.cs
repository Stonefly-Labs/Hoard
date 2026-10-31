using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Fixtures.Metadata.Sqlite;

namespace Hoard.Fixtures.Metadata.Hosting;

public sealed partial class MetadataFixtureSession
{
    private readonly ConcurrentDictionary<string, CorruptionOwner> corruptionOwners = new(StringComparer.Ordinal);
    private readonly object corruptionLifecycle = new();
    private bool corruptionClosing;

    public async ValueTask RestoreCorruptionsForTestAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        foreach (var owner in corruptionOwners.Values)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (Volatile.Read(ref owner.Applying) != 0)
            { throw new InvalidOperationException("Metadata corruption application is still owned."); }
            await (owner.Scope ?? throw new InvalidOperationException("Metadata corruption scope is unavailable.")).DisposeAsync();
        }
    }

    public ValueTask<MetadataFixtureCorruptionScope> CorruptRecordPayloadForTestAsync(
        MetadataSelector selector, string shape, string canary, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var key = "record:" + Convert.ToHexStringLower(MetadataEncoding.Key(selector).AsSpan());
        return Store switch
        {
            SqliteMetadataStore sqlite => ApplyCorruptionAsync(key,
                async () => PayloadValue(await sqlite.ObserveRecordPayloadForTestAsync(selector, default)),
                original => SqlitePayloadDamage.Record(original, shape, canary),
                async (original, damaged, applied) =>
                { PayloadValue(await sqlite.CompareExchangeRecordPayloadForTestAsync(selector, original, damaged, applied)); },
                async value => { PayloadValue(await sqlite.ReplaceRecordPayloadForTestAsync(selector, value)); },
                value => PayloadHash(Encoding.UTF8.GetBytes(value)), cancellationToken),
            MemoryMetadataStore memory => ApplyCorruptionAsync(key,
                async () => PayloadValue(await memory.RecordPayloadForTestAsync(selector)),
                original => MemoryPayloadDamage.Record(original, shape, canary),
                async (original, damaged, applied) =>
                { PayloadValue(await memory.CompareExchangeRecordPayloadForTestAsync(selector, original, damaged, applied)); },
                async value => { PayloadValue(await memory.ReplaceRecordPayloadForTestAsync(selector, value)); },
                value => PayloadHash(Encoding.UTF8.GetBytes(value)), cancellationToken),
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        };
    }

    public ValueTask<MetadataFixtureCorruptionScope> CorruptOperationPayloadForTestAsync(
        MetadataOperationTicket ticket, string shape, MetadataOperationTicket foreignTicket,
        string canary, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(ticket);
        var key = $"operation:{ticket.Epoch.Value:N}:{ticket.Id.Value:N}";
        return Store switch
        {
            SqliteMetadataStore sqlite => ApplyCorruptionAsync(key,
                async () => PayloadValue(await sqlite.ObserveOperationImageForTestAsync(ticket, default)),
                original => SqlitePayloadDamage.Operation(original,
                    shape == "invalid-fingerprint" ? "text-fingerprint" : shape, foreignTicket, canary),
                async (original, damaged, applied) =>
                { PayloadValue(await sqlite.CompareExchangeOperationImageForTestAsync(ticket, original, damaged, applied)); },
                async value => { PayloadValue(await sqlite.ReplaceOperationImageForTestAsync(ticket, value)); },
                value => PayloadHash(JsonSerializer.SerializeToUtf8Bytes(value)), cancellationToken),
            MemoryMetadataStore memory => ApplyCorruptionAsync(key,
                async () => PayloadValue(await memory.OperationImageForTestAsync(ticket)),
                original => MemoryPayloadDamage.Operation(original, shape, foreignTicket, canary),
                async (original, damaged, applied) =>
                { PayloadValue(await memory.CompareExchangeOperationImageForTestAsync(ticket, original, damaged, applied)); },
                async value => { PayloadValue(await memory.ReplaceOperationImageForTestAsync(ticket, value)); },
                value => PayloadHash(JsonSerializer.SerializeToUtf8Bytes(value)), cancellationToken),
            _ => throw new InvalidOperationException("Unknown metadata fixture.")
        };
    }

    private async ValueTask<MetadataFixtureCorruptionScope> ApplyCorruptionAsync<T>(
        string key, Func<ValueTask<T>> read, Func<T, T> damage,
        Func<T, T, Action, ValueTask> replace, Func<T, ValueTask> write,
        Func<T, string> fingerprint, CancellationToken cancellationToken)
    {
        var owner = new CorruptionOwner();
        lock (corruptionLifecycle)
        {
            if (corruptionClosing)
            { throw new InvalidOperationException("Metadata fixture closure has been admitted."); }
            if (!corruptionOwners.TryAdd(key, owner))
            { throw new InvalidOperationException("Metadata corruption already owned."); }
        }
        MetadataFixtureCorruptionScope? scope = null;
        var submitted = false;
        var applied = false;
        var handedOff = false;
        try
        {
            var original = await read();
            var damaged = damage(original);
            scope = new(fingerprint(original), async () => fingerprint(await read()),
                async () =>
                {
                    await WhenIdleAsync();
                    if (!Volatile.Read(ref applied)) { return false; }
                    await write(original);
                    await WhenIdleAsync();
                    return true;
                }, () => corruptionOwners.TryRemove(new KeyValuePair<string, CorruptionOwner>(key, owner)));
            owner.Scope = scope;
            await Controls.ObserveAsync("corruption.captured");
            cancellationToken.ThrowIfCancellationRequested();
            submitted = true;
            await replace(original, damaged, () => Volatile.Write(ref applied, true));
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
                    if (submitted && scope is not null) { await scope.DisposeAsync(); }
                    else { corruptionOwners.TryRemove(new KeyValuePair<string, CorruptionOwner>(key, owner)); }
                }
            }
            finally { Volatile.Write(ref owner.Applying, 0); }
        }
    }

    private sealed class CorruptionOwner
    {
        public int Applying = 1;
        public MetadataFixtureCorruptionScope? Scope;
    }

    private void BeginCorruptionClosure()
    {
        lock (corruptionLifecycle)
        {
            if (!corruptionOwners.IsEmpty)
            { throw new InvalidOperationException("Metadata corruption scope must settle before fixture closure."); }
            corruptionClosing = true;
        }
    }

    private static string PayloadHash(byte[] value) => Convert.ToHexStringLower(SHA256.HashData(value));

    private static T PayloadValue<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new InvalidOperationException("FaultControl." + failure.Code),
        _ => throw new InvalidOperationException("Unknown metadata outcome.")
    };
}

public sealed class MetadataFixtureCorruptionScope : IAsyncDisposable
{
    private readonly Func<ValueTask<string>> observe;
    private readonly Func<ValueTask<bool>> restore;
    private readonly Action release;
    private readonly SemaphoreSlim restoring = new(1, 1);
    private bool restored;

    internal MetadataFixtureCorruptionScope(
        string originalSha256, Func<ValueTask<string>> observe, Func<ValueTask<bool>> restore, Action release)
    {
        OriginalSha256 = originalSha256;
        this.observe = observe;
        this.restore = restore;
        this.release = release;
    }

    public string OriginalSha256 { get; }

    public ValueTask<string> ObserveSha256Async(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return observe();
    }

    public async ValueTask DisposeAsync()
    {
        if (!await restoring.WaitAsync(TimeSpan.FromSeconds(5)))
        { throw new InvalidOperationException("Metadata corruption restoration is still owned."); }
        try
        {
            if (restored) { return; }
            if (await restore() && await observe() != OriginalSha256)
            { throw new InvalidOperationException("Metadata corruption restoration did not preserve the original payload."); }
            restored = true;
            release();
        }
        finally { restoring.Release(); }
    }
}
