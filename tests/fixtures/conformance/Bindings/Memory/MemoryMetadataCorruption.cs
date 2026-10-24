using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Bindings.Memory;

internal sealed partial class MemoryMetadataFaults
{
    public ValueTask<MetadataContinuation> CorruptContinuationAsync(
        MetadataContinuation continuation, MetadataContinuationComponent component,
        MetadataContinuationCorruption corruption, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var field = component switch
        {
            MetadataContinuationComponent.ContractVersion => "Contract",
            MetadataContinuationComponent.Epoch or MetadataContinuationComponent.Schema => "Epoch",
            MetadataContinuationComponent.Query => "Query",
            MetadataContinuationComponent.PageSize => "Size",
            MetadataContinuationComponent.Position => "After",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var shape = corruption switch
        {
            MetadataContinuationCorruption.Null => "null",
            MetadataContinuationCorruption.Omitted => "omitted",
            MetadataContinuationCorruption.WrongType => "wrong-type",
            MetadataContinuationCorruption.Empty => "empty",
            MetadataContinuationCorruption.OddHex => "odd-hex",
            MetadataContinuationCorruption.InvalidHex => "invalid-hex",
            _ => throw new ArgumentException("BindingInvalid")
        };
        return ValueTask.FromResult(MemoryPayloadDamage.Continuation(continuation, field, shape));
    }

    public async ValueTask<IMetadataCorruptionScope> CorruptAsync(
        MetadataCorruptionRequest request, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (request is MetadataCorruptionRequest.Record record)
        {
            var original = Value(await Store.RecordPayloadForTestAsync(record.Selector));
            var shape = record.Corruption switch
            {
                MetadataRecordCorruption.NullLabel => "null-label",
                MetadataRecordCorruption.OversizedLabel => "oversized-label",
                MetadataRecordCorruption.NullRevision => "null-revision",
                MetadataRecordCorruption.MalformedEncoding => "malformed",
                MetadataRecordCorruption.MismatchedKey => "wrong-key",
                MetadataRecordCorruption.CacheAuthorization => "cache-auth",
                MetadataRecordCorruption.AggregateAuthorization => "aggregate-auth",
                MetadataRecordCorruption.AggregateStart => "aggregate-start",
                MetadataRecordCorruption.AggregateEnd => "aggregate-end",
                MetadataRecordCorruption.LeaseResource => "lease-resource",
                _ => throw new ArgumentException("BindingInvalid")
            };
            var damaged = MemoryPayloadDamage.Record(original, shape, MetadataReconciliationAssertions.CorruptionCanary);
            cancellationToken.ThrowIfCancellationRequested();
            Value(await Store.ReplaceRecordPayloadForTestAsync(record.Selector, damaged));
            return new CorruptionScope<string>(original,
                async () => Value(await Store.RecordPayloadForTestAsync(record.Selector)),
                async value => { Value(await Store.ReplaceRecordPayloadForTestAsync(record.Selector, value)); },
                value => Fingerprint(Encoding.UTF8.GetBytes(value)));
        }
        if (request is not MetadataCorruptionRequest.Operation operation) { throw new ArgumentException("BindingInvalid"); }
        var image = Value(await Store.OperationImageForTestAsync(operation.Ticket));
        var operationShape = operation.Corruption switch
        {
            MetadataOperationCorruption.NullTarget => "null-target",
            MetadataOperationCorruption.NullRevision => "null-revision",
            MetadataOperationCorruption.MalformedEncoding => "malformed",
            MetadataOperationCorruption.MissingRevisions => "missing-revisions",
            MetadataOperationCorruption.OversizedRevisions => "oversized-revisions",
            MetadataOperationCorruption.OversizedEncoding => "oversized-payload",
            MetadataOperationCorruption.MismatchedTicket => "mismatched-ticket",
            MetadataOperationCorruption.MissingReceipt => "missing-receipt",
            MetadataOperationCorruption.ShortFingerprint => "short-fingerprint",
            MetadataOperationCorruption.MissingFingerprint => "missing-fingerprint",
            MetadataOperationCorruption.InvalidFingerprintEncoding => "invalid-fingerprint",
            MetadataOperationCorruption.ReservedReceipt => "reserved-receipt",
            MetadataOperationCorruption.AbandonedReceipt => "abandoned-receipt",
            MetadataOperationCorruption.InvalidState => "fractional-state",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var damagedImage = MemoryPayloadDamage.Operation(image, operationShape,
            operation.ForeignTicket, MetadataReconciliationAssertions.CorruptionCanary);
        cancellationToken.ThrowIfCancellationRequested();
        Value(await Store.ReplaceOperationImageForTestAsync(operation.Ticket, damagedImage));
        return new CorruptionScope<MemoryOperationTestImage>(image,
            async () => Value(await Store.OperationImageForTestAsync(operation.Ticket)),
            async value => { Value(await Store.ReplaceOperationImageForTestAsync(operation.Ticket, value)); },
            value => Fingerprint(JsonSerializer.SerializeToUtf8Bytes(value)));
    }

    private static T Value<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new InvalidOperationException("FaultControl." + failure.Code),
        _ => throw new InvalidOperationException("BindingInvalid")
    };

    private static ConformanceStateFingerprint Fingerprint(byte[] bytes) =>
        new(Convert.ToHexStringLower(SHA256.HashData(bytes)));

    private sealed class CorruptionScope<T>(T original, Func<ValueTask<T>> read,
        Func<T, ValueTask> restore, Func<T, ConformanceStateFingerprint> fingerprint) : IMetadataCorruptionScope
    {
        private readonly SemaphoreSlim restoring = new(1, 1);
        private bool restored;
        public ConformanceStateFingerprint Original { get; } = fingerprint(original);

        public async ValueTask<ConformanceStateFingerprint> ObserveAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return fingerprint(await read());
        }

        public async ValueTask DisposeAsync()
        {
            if (!await restoring.WaitAsync(TimeSpan.FromSeconds(5))) { throw new InvalidOperationException("BindingInvalid"); }
            try
            {
                if (restored) { return; }
                await restore(original);
                restored = true;
            }
            finally { restoring.Release(); }
        }
    }
}
