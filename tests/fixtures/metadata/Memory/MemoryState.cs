using System.Buffers.Binary;
using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed class MemoryFixtureImage
{
    internal MemoryFixtureImage(MemoryState state) => State = state;
    internal MemoryState State { get; }
    public string ComputeFingerprint(CancellationToken cancellationToken)
    {
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        Append("f07-memory-image-v1");
        Append(new { State.Schema, State.Epoch, State.TimeFloor, State.Changes });
        Append("records");
        Append(State.Records.Encoded.Count());
        foreach (var pair in State.Records.Encoded.OrderBy(pair => JsonSerializer.Serialize(pair.Key), StringComparer.Ordinal))
        { Append(pair); }
        Append("edges");
        Append(State.Edges.Count);
        foreach (var pair in State.Edges.OrderBy(pair => JsonSerializer.Serialize(pair.Key), StringComparer.Ordinal))
        { Append(pair); }
        Append("dependents");
        Append(State.Dependents.Count);
        foreach (var pair in State.Dependents.OrderBy(pair => JsonSerializer.Serialize(pair.Key), StringComparer.Ordinal))
        {
            Append(pair.Key);
            Append(pair.Value.Count);
            foreach (var dependent in pair.Value.OrderBy(value => JsonSerializer.Serialize(value), StringComparer.Ordinal))
            { Append(dependent); }
        }
        Append("operations");
        Append(State.Operations.Count);
        foreach (var pair in State.Operations.OrderBy(pair => pair.Key.Value)) { Append(pair); }
        return Convert.ToHexStringLower(hash.GetHashAndReset());

        void Append<T>(T value)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var bytes = JsonSerializer.SerializeToUtf8Bytes(value);
            Span<byte> length = stackalloc byte[4];
            BinaryPrimitives.WriteInt32BigEndian(length, bytes.Length);
            hash.AppendData(length);
            hash.AppendData(bytes);
        }
    }
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
