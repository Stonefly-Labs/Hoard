using System.Collections.Concurrent;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Bindings.Memory;

internal sealed class MemoryPublicationAuthority : IMetadataConformanceAuthority
{
    private readonly ConcurrentDictionary<string, MetadataCommittedArtifact> artifacts = new(StringComparer.Ordinal);
    private int acquisitions;
    private int active;
    public int Acquisitions => Volatile.Read(ref acquisitions);
    public int ActiveGuards => Volatile.Read(ref active);

    public MetadataArtifactEvidence Register(ArtifactDigest digest, long length)
    {
        var artifact = new MetadataCommittedArtifact(digest, length);
        var evidence = new MetadataArtifactEvidence(Guid.NewGuid().ToString("N"));
        if (!artifacts.TryAdd(evidence.Value, artifact)) { throw new InvalidOperationException("BindingInvalid"); }
        return evidence;
    }

    public void Revoke(MetadataArtifactEvidence evidence)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        if (!artifacts.TryRemove(evidence.Value, out _)) { throw new ArgumentException("BindingInvalid"); }
    }

    public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
        MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken)
    {
        Interlocked.Increment(ref acquisitions);
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(evidence);
        ArgumentNullException.ThrowIfNull(options);
        if (!artifacts.TryGetValue(evidence.Value, out var artifact))
        {
            return ValueTask.FromResult<MetadataResult<IMetadataPublicationGuard>>(
                new MetadataResult<IMetadataPublicationGuard>.Failure(MetadataFailureCode.InvalidInput,
                    MetadataPhase.Publication, MetadataRetryDisposition.CorrectInput, new(Guid.NewGuid())));
        }
        Interlocked.Increment(ref active);
        return ValueTask.FromResult<MetadataResult<IMetadataPublicationGuard>>(
            new MetadataResult<IMetadataPublicationGuard>.Success(new Guard(this, artifact)));
    }

    private sealed class Guard(MemoryPublicationAuthority owner, MetadataCommittedArtifact artifact) : IMetadataPublicationGuard
    {
        private int disposed;
        public MetadataCommittedArtifact Artifact { get; } = artifact;
        public ValueTask DisposeAsync()
        {
            if (Interlocked.Exchange(ref disposed, 1) == 0) { Interlocked.Decrement(ref owner.active); }
            return ValueTask.CompletedTask;
        }
    }
}
