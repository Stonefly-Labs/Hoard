using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed class MemoryFixtureImage
{
    internal MemoryFixtureImage(MemoryState state) => State = state;
    internal MemoryState State { get; }
    public override string ToString() => "Memory fixture logical image (non-durable)";
}

internal sealed record MemoryOperation(
    MetadataOperationTicket Ticket, double State, string? Fingerprint, string? Receipt);

internal sealed record MemoryState(
    int Schema, MetadataId Epoch, long TimeFloor, long Changes,
    MemoryStoredRecords Records,
    ImmutableDictionary<MetadataRequestIdentity, ArtifactDigest> Edges,
    ImmutableDictionary<MetadataSelector, ImmutableHashSet<MetadataSelector>> Dependents,
    ImmutableDictionary<MetadataId, MemoryOperation> Operations)
{
    public static MemoryState Empty(int schema) => new(schema, new(Guid.NewGuid()), 0, 0,
        MemoryStoredRecords.Empty,
        ImmutableDictionary<MetadataRequestIdentity, ArtifactDigest>.Empty,
        ImmutableDictionary<MetadataSelector, ImmutableHashSet<MetadataSelector>>.Empty,
        ImmutableDictionary<MetadataId, MemoryOperation>.Empty);
}

internal sealed class MemoryContractFailure(MetadataFailureCode code) : Exception("Memory metadata contract rejected work.")
{
    public MetadataFailureCode Code { get; } = code;
}
