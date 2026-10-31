using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed record MemoryOperationTestImage(double State, string? Fingerprint, string? Receipt);

public sealed partial class MemoryMetadataStore
{
    public ValueTask<MetadataResult<string>> RecordPayloadForTestAsync(MetadataSelector selector) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            await EnterWriterAsync(activity);
            try { return Success(state.Records.Payload(selector)); }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MetadataId>> ReplaceRecordPayloadForTestAsync(MetadataSelector selector, string payload) =>
        ReplaceRecordPayloadAsync(selector, payload, null, null);

    public ValueTask<MetadataResult<MetadataId>> CompareExchangeRecordPayloadForTestAsync(
        MetadataSelector selector, string expected, string payload, Action? applied = null)
    {
        ArgumentNullException.ThrowIfNull(expected);
        return ReplaceRecordPayloadAsync(selector, payload, expected, applied);
    }

    private ValueTask<MetadataResult<MetadataId>> ReplaceRecordPayloadAsync(
        MetadataSelector selector, string payload, string? expected, Action? applied) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            ArgumentNullException.ThrowIfNull(payload);
            if (payload.Length > MetadataEncoding.MaximumBytes * 2) { throw new ArgumentException("Synthetic payload exceeds bounds."); }
            await EnterWriterAsync(activity);
            try
            {
                if (expected is not null && state.Records.Payload(selector) != expected)
                { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
                Volatile.Write(ref state, state with { Records = state.Records.WithPayload(selector, payload) });
                applied?.Invoke();
                await observe("memory.persisted.changed");
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MemoryOperationTestImage>> OperationImageForTestAsync(MetadataOperationTicket ticket) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            MetadataEncoding.ValidateTicket(ticket);
            await EnterWriterAsync(activity);
            try
            {
                if (!state.Operations.TryGetValue(ticket.Id, out var operation) || operation.Ticket != ticket)
                { throw new ArgumentException("Missing synthetic operation."); }
                return Success(new MemoryOperationTestImage(operation.State, operation.Fingerprint, operation.Receipt));
            }
            finally { writer.Release(); }
        });

    public ValueTask<MetadataResult<MetadataId>> ReplaceOperationImageForTestAsync(
        MetadataOperationTicket ticket, MemoryOperationTestImage image) =>
        ReplaceOperationImageAsync(ticket, image, null, null);

    public ValueTask<MetadataResult<MetadataId>> CompareExchangeOperationImageForTestAsync(
        MetadataOperationTicket ticket, MemoryOperationTestImage expected, MemoryOperationTestImage image, Action? applied = null)
    {
        ArgumentNullException.ThrowIfNull(expected);
        return ReplaceOperationImageAsync(ticket, image, expected, applied);
    }

    private ValueTask<MetadataResult<MetadataId>> ReplaceOperationImageAsync(
        MetadataOperationTicket ticket, MemoryOperationTestImage image, MemoryOperationTestImage? expected, Action? applied) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, true, async activity =>
        {
            ArgumentNullException.ThrowIfNull(image);
            MetadataEncoding.ValidateTicket(ticket);
            if (!double.IsFinite(image.State) || image.Fingerprint is { Length: > 128 }
                || image.Receipt is { } payload && payload.Length > MetadataEncoding.MaximumBytes * 2)
            { throw new ArgumentException("Synthetic operation exceeds bounds."); }
            await EnterWriterAsync(activity);
            try
            {
                if (!state.Operations.TryGetValue(ticket.Id, out var operation) || operation.Ticket != ticket)
                { throw new ArgumentException("Missing synthetic operation."); }
                if (expected is not null && new MemoryOperationTestImage(operation.State, operation.Fingerprint, operation.Receipt) != expected)
                { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
                var replacement = operation with { State = image.State, Fingerprint = image.Fingerprint, Receipt = image.Receipt };
                Volatile.Write(ref state, state with { Operations = state.Operations.SetItem(ticket.Id, replacement) });
                applied?.Invoke();
                await observe("memory.persisted.changed");
                return Success(state.Epoch);
            }
            finally { writer.Release(); }
        });
}
