using Hoard.Abstractions.Metadata;

namespace Hoard.Testing.Conformance.Bindings;

public enum MetadataContinuationComponent { ContractVersion, Epoch, Schema, Query, PageSize, Position }
public enum MetadataContinuationCorruption { Null, Omitted, WrongType, Empty, OddHex, InvalidHex }

public delegate ValueTask<MetadataContinuation> MetadataContinuationCorruptionControl(
    MetadataContinuation continuation, MetadataContinuationComponent component,
    MetadataContinuationCorruption corruption, CancellationToken cancellationToken);
