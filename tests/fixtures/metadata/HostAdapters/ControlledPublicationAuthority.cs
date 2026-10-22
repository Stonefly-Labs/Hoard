using System.Collections.Concurrent;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Hosting;

public sealed class MetadataFixtureControls
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> observers = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<string> diagnostics = new();
    private int activities;
    public int ActivityCount => Volatile.Read(ref activities);
    public string[] Diagnostics => diagnostics.ToArray();
    public void SetObserver(string point, Func<ValueTask> observer) => observers[point] = observer;
    public void RemoveObserver(string point) => observers.TryRemove(point, out _);
    public ValueTask ObserveAsync(string point)
    {
        Interlocked.Increment(ref activities);
        return observers.TryGetValue(point, out var observer) ? observer() : ValueTask.CompletedTask;
    }
    public void Diagnose(string code) => diagnostics.Enqueue(code);
}

public sealed class ControlledPublicationAuthority(MetadataFixtureControls controls) : IMetadataPublicationAuthority
{
    private readonly ConcurrentDictionary<string, MetadataCommittedArtifact> artifacts = new(StringComparer.Ordinal);
    private int active;
    private int acquisitions;
    public int ActiveGuards => Volatile.Read(ref active);
    public int Acquisitions => Volatile.Read(ref acquisitions);

    public MetadataArtifactEvidence Register(ArtifactDigest digest, long length)
    {
        if (length < 0) { throw new ArgumentException("Artifact length must be nonnegative."); }
        var evidence = new MetadataArtifactEvidence(Guid.NewGuid().ToString("N"));
        artifacts[evidence.Value] = new(digest, length);
        return evidence;
    }

    public void Revoke(MetadataArtifactEvidence evidence) => artifacts.TryRemove(evidence.Value, out _);

    public async ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
        MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken)
    {
        Interlocked.Increment(ref acquisitions);
        await controls.ObserveAsync("authority.acquire");
        if (cancellationToken.IsCancellationRequested || !artifacts.TryGetValue(evidence.Value, out var artifact))
        {
            return new MetadataResult<IMetadataPublicationGuard>.Failure(MetadataFailureCode.InvalidInput,
                MetadataPhase.Publication, MetadataRetryDisposition.CorrectInput, new(Guid.NewGuid()));
        }
        Interlocked.Increment(ref active);
        return new MetadataResult<IMetadataPublicationGuard>.Success(new Guard(this, artifact, controls));
    }

    private sealed class Guard(ControlledPublicationAuthority owner, MetadataCommittedArtifact artifact,
        MetadataFixtureControls controls) : IMetadataPublicationGuard
    {
        private int disposed;
        public MetadataCommittedArtifact Artifact { get; } = artifact;
        public async ValueTask DisposeAsync()
        {
            if (Interlocked.Exchange(ref disposed, 1) == 0)
            {
                try { await controls.ObserveAsync("authority.release"); }
                finally { Interlocked.Decrement(ref owner.active); }
            }
        }
    }
}
