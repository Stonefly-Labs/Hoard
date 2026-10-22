using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed class ArtifactMetadataPublicationAuthority(
    ArtifactStoreIdentity selectedStore, IArtifactEvidenceValidator validator,
    IArtifactCoordinationAuthority authority, TimeProvider? timeProvider = null) : IMetadataPublicationAuthority
{
    private readonly TimeProvider clock = timeProvider ?? TimeProvider.System;

    public MetadataArtifactEvidence Encode(ArtifactCommitEvidence evidence)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        if (evidence.Stamp.Store != selectedStore) { throw new ArgumentException("Foreign artifact evidence."); }
        var stamp = evidence.Stamp;
        var descriptor = new EvidenceDescriptor(1, selectedStore.ProviderModuleId, selectedStore.InstanceId,
            selectedStore.Epoch, stamp.Incarnation, stamp.Identity.Digest.Hex, stamp.Identity.Length,
            evidence.TicketId, evidence.ReceiptId, evidence.ProofHandle, evidence.Outcome);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(descriptor);
        if (bytes.Length > 12288) { throw new ArgumentException("Artifact metadata reference exceeds its bound."); }
        return new MetadataArtifactEvidence(Convert.ToBase64String(bytes));
    }

    public async ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
        MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        ArgumentNullException.ThrowIfNull(options);
        var started = clock.GetTimestamp();
        var budget = options.EffectiveTimeout;
        if (budget < TimeSpan.FromMilliseconds(1) || budget > TimeSpan.FromSeconds(30))
        { return Failure(MetadataFailureCode.InvalidInput); }
        ArtifactCommitEvidence committed;
        try
        {
            if (evidence.Value.Length > 16384) { return Failure(MetadataFailureCode.InvalidInput); }
            var bytes = Convert.FromBase64String(evidence.Value);
            if (bytes.Length > 12288) { return Failure(MetadataFailureCode.InvalidInput); }
            var descriptor = JsonSerializer.Deserialize<EvidenceDescriptor>(bytes);
            if (descriptor is null || descriptor.Version != 1) { return Failure(MetadataFailureCode.InvalidInput); }
            var store = new ArtifactStoreIdentity(descriptor.ModuleId, descriptor.Instance, descriptor.Epoch);
            if (store != selectedStore) { return Failure(MetadataFailureCode.InvalidInput); }
            var stamp = new ArtifactStamp(store, new ArtifactIdentity(new ArtifactDigest(descriptor.Digest), descriptor.Length),
                descriptor.Incarnation);
            committed = new ArtifactCommitEvidence(stamp, descriptor.Ticket, descriptor.Receipt, descriptor.Proof, descriptor.Outcome);
        }
        catch (Exception error) when (error is JsonException or FormatException or ArgumentException)
        { return Failure(MetadataFailureCode.InvalidInput); }
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            selectedStore, committed.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(committed.Stamp));
        var remaining = budget - clock.GetElapsedTime(started);
        if (remaining < TimeSpan.FromMilliseconds(1)) { return Failure(MetadataFailureCode.DeadlineExceeded); }
        var admitted = await authority.AcquireAsync(request, new(remaining), cancellationToken);
        if (admitted is not ArtifactResult<IArtifactProtectionGuard>.Success acquired)
        { return Failure(Map(admitted)); }
        var protection = acquired.Value;
        var transferred = false;
        try
        {
            remaining = budget - clock.GetElapsedTime(started);
            if (remaining < TimeSpan.FromMilliseconds(1)) { return Failure(MetadataFailureCode.DeadlineExceeded); }
            var result = await validator.ValidateAsync(committed, protection, new(remaining), cancellationToken);
            if (result is not ArtifactResult<ArtifactStamp>.Success validated)
            { return Failure(Map(result)); }
            if (validated.Value != committed.Stamp) { return Failure(MetadataFailureCode.Conflict); }
            transferred = true;
            return new MetadataResult<IMetadataPublicationGuard>.Success(new Guard(protection,
                new MetadataCommittedArtifact(validated.Value.Identity.Digest, validated.Value.Identity.Length)));
        }
        finally
        {
            if (!transferred) { await protection.DisposeAsync(); }
        }
    }

    private static MetadataFailureCode Map<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Failure failure ? failure.Code switch
        {
            ArtifactFailureCode.InvalidInput or ArtifactFailureCode.ReconciliationExpired => MetadataFailureCode.InvalidInput,
            ArtifactFailureCode.Conflict or ArtifactFailureCode.NotFound or ArtifactFailureCode.Denied
                or ArtifactFailureCode.CorruptContent => MetadataFailureCode.Conflict,
            ArtifactFailureCode.CancelledBeforeCommit => MetadataFailureCode.CancelledBeforeCommit,
            ArtifactFailureCode.DeadlineExceeded => MetadataFailureCode.DeadlineExceeded,
            ArtifactFailureCode.Disposed => MetadataFailureCode.Disposed,
            _ => MetadataFailureCode.Unavailable
        } : MetadataFailureCode.InternalFailure;

    private static MetadataResult<IMetadataPublicationGuard> Failure(MetadataFailureCode code)
        => new MetadataResult<IMetadataPublicationGuard>.Failure(code, MetadataPhase.Publication,
            MetadataRetryDisposition.None, new(Guid.NewGuid()));

    private sealed record EvidenceDescriptor(int Version, string ModuleId, Guid Instance, Guid Epoch, Guid Incarnation,
        string Digest, long Length, Guid Ticket, Guid Receipt, string Proof, ArtifactPublicationOutcome Outcome);

    private sealed class Guard(IArtifactProtectionGuard protection, MetadataCommittedArtifact artifact) : IMetadataPublicationGuard
    {
        private int disposed;
        public MetadataCommittedArtifact Artifact { get; } = artifact;
        public async ValueTask DisposeAsync()
        {
            if (Interlocked.Exchange(ref disposed, 1) == 0) { await protection.DisposeAsync(); }
        }
    }
}
