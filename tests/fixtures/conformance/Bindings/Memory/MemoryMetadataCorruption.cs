using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Shared;
using Hoard.Fixtures.Metadata.Memory;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Bindings.Memory;

internal sealed partial class MemoryMetadataFaults
{
    private readonly MetadataCorruptionOwnership corruptions = new(context.ControlBudget);
    public bool CorruptionsClosing => corruptions.IsClosing;
    public void BeginCorruptionClosure() => corruptions.BeginClosure();
    public ValueTask RestoreCorruptionsAsync(CancellationToken cancellationToken) => corruptions.RestoreAsync(cancellationToken);

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
            return await corruptions.ApplyAsync(request,
                async () => Value(await Store.RecordPayloadForTestAsync(record.Selector)),
                original => MemoryPayloadDamage.Record(original, shape, MetadataReconciliationAssertions.CorruptionCanary),
                async (original, damaged, applied) =>
                { Value(await Store.CompareExchangeRecordPayloadForTestAsync(record.Selector, original, damaged, applied)); },
                async value => { Value(await Store.ReplaceRecordPayloadForTestAsync(record.Selector, value)); },
                value => Fingerprint(Encoding.UTF8.GetBytes(value)),
                () => OnBoundaryAsync("corruption.captured"), AwaitSettlementAsync, cancellationToken);
        }
        if (request is not MetadataCorruptionRequest.Operation operation) { throw new ArgumentException("BindingInvalid"); }
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
        return await corruptions.ApplyAsync(request,
            async () => Value(await Store.OperationImageForTestAsync(operation.Ticket)),
            image => MemoryPayloadDamage.Operation(image, operationShape,
                operation.ForeignTicket, MetadataReconciliationAssertions.CorruptionCanary),
            async (image, damaged, applied) =>
            { Value(await Store.CompareExchangeOperationImageForTestAsync(operation.Ticket, image, damaged, applied)); },
            async value => { Value(await Store.ReplaceOperationImageForTestAsync(operation.Ticket, value)); },
            value => Fingerprint(JsonSerializer.SerializeToUtf8Bytes(value)),
            () => OnBoundaryAsync("corruption.captured"), AwaitSettlementAsync, cancellationToken);
    }

    private static T Value<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new InvalidOperationException("FaultControl." + failure.Code),
        _ => throw new InvalidOperationException("BindingInvalid")
    };

    private static ConformanceStateFingerprint Fingerprint(byte[] bytes) =>
        new(Convert.ToHexStringLower(SHA256.HashData(bytes)));

}
