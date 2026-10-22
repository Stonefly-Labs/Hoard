using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore
{
    private long Now(MemoryState root)
    {
        var value = Math.Max(root.TimeFloor, clock.GetUtcNow().ToUnixTimeMilliseconds());
        _ = new MetadataInstant(value);
        return value;
    }

    private static MemoryOperation? Operation(MemoryState root, MetadataOperationTicket ticket, long now)
    {
        MetadataEncoding.ValidateTicket(ticket);
        return ticket.Epoch == root.Epoch && now < ticket.Expires.UnixMilliseconds
            && root.Operations.TryGetValue(ticket.Id, out var operation) && operation.Ticket == ticket ? operation : null;
    }

    private async ValueTask<MetadataResult<MetadataOperationTicket>> ReserveCoreAsync(MemoryActivity activity)
    {
        await EnterWriterAsync(activity);
        try
        {
            var root = state;
            var now = Now(root);
            var operations = root.Operations;
            var pruned = 0;
            foreach (var pair in root.Operations)
            {
                activity.Check();
                if (pair.Value.Ticket.Expires.UnixMilliseconds <= now)
                {
                    operations = operations.Remove(pair.Key);
                    if (++pruned == 100) { break; }
                }
            }
            if (operations.Count >= 100000)
            {
                Volatile.Write(ref state, root with { TimeFloor = now, Operations = operations });
                throw new MemoryContractFailure(MetadataFailureCode.Capacity);
            }
            var ticket = new MetadataOperationTicket(root.Epoch, new(Guid.NewGuid()), new(now), new(checked(now + 86400000)));
            var next = root with { TimeFloor = now, Operations = operations.Add(ticket.Id, new(ticket, 0, null, null)) };
            await observe("reserve.before_commit");
            activity.Check();
            Volatile.Write(ref state, next);
            return Success(ticket);
        }
        finally { writer.Release(); }
    }

    private async ValueTask<MetadataResult<MetadataResolution>> ReconcileCoreAsync(MetadataOperationTicket ticket, MemoryActivity activity)
    {
        MetadataEncoding.ValidateTicket(ticket);
        await EnterWriterAsync(activity);
        try
        {
            var current = state;
            var now = Now(current);
            current = current with { TimeFloor = now };
            Volatile.Write(ref state, current);
            var operation = Operation(current, ticket, now);
            if (operation is null) { throw new MemoryContractFailure(MetadataFailureCode.ReconciliationExpired); }
            if (operation.State == 1)
            { return Success<MetadataResolution>(new MetadataResolution.Committed(operation.Receipt ?? throw new MemoryContractFailure(MetadataFailureCode.CorruptState))); }
            var next = current with { Operations = current.Operations.SetItem(ticket.Id, operation with { State = 2 }) };
            await observe("reconcile.before_decision");
            activity.CommitDecision();
            Volatile.Write(ref state, next);
            activity.Committed();
            return Success<MetadataResolution>(new MetadataResolution.NotCommitted(ticket));
        }
        finally { writer.Release(); }
    }

    private async ValueTask<MetadataResult<MetadataCommitReceipt>> CommitCoreAsync(MetadataMutationBatch request, MemoryActivity activity)
    {
        _ = MetadataEncoding.Encode(request);
        var fingerprint = Convert.ToHexStringLower(MetadataEncoding.Fingerprint(request).AsSpan());
        await EnterWriterAsync(activity);
        try
        {
            var initial = state with { TimeFloor = Now(state) };
            Volatile.Write(ref state, initial);
            var reserved = Operation(initial, request.Ticket, initial.TimeFloor)
                ?? throw new MemoryContractFailure(MetadataFailureCode.ReconciliationExpired);
            if (reserved.State == 1)
            {
                return reserved.Fingerprint == fingerprint
                    ? Success(reserved.Receipt ?? throw new MemoryContractFailure(MetadataFailureCode.CorruptState))
                    : Failure<MetadataCommitReceipt>(MetadataFailureCode.Conflict, MetadataPhase.Commit);
            }
            if (reserved.State != 0) { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
        }
        finally { writer.Release(); }
        var guards = new List<IMetadataPublicationGuard>();
        try
        {
            var required = new Dictionary<ArtifactDigest, MetadataMutation.PublishCacheEntry>();
            foreach (var publication in request.Mutations.OfType<MetadataMutation.PublishCacheEntry>())
            {
                if (required.TryGetValue(publication.Record.Digest, out var prior) && prior.Record.Length != publication.Record.Length)
                { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                required.TryAdd(publication.Record.Digest, publication);
            }
            foreach (var publication in required.Values)
            {
                activity.Check();
                await observe("publication.acquire");
                var result = await authority.AcquireAsync(publication.Evidence, new(activity.Remaining), CancellationToken.None);
                if (result is not MetadataResult<IMetadataPublicationGuard>.Success accepted)
                {
                    throw new MemoryContractFailure(result is MetadataResult<IMetadataPublicationGuard>.Failure failure
                        ? failure.Code : MetadataFailureCode.InternalFailure);
                }
                guards.Add(accepted.Value);
                if (accepted.Value.Artifact is not { } artifact
                    || artifact.Digest != publication.Record.Digest || artifact.Length != publication.Record.Length)
                { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
            }
            await EnterWriterAsync(activity);
            try
            {
                var previous = state;
                var now = Now(previous);
                Volatile.Write(ref state, previous with { TimeFloor = now });
                var operation = Operation(previous, request.Ticket, now)
                    ?? throw new MemoryContractFailure(MetadataFailureCode.ReconciliationExpired);
                if (operation.State != 0)
                {
                    return operation.State == 1 && operation.Fingerprint == fingerprint
                        ? Success(operation.Receipt ?? throw new MemoryContractFailure(MetadataFailureCode.CorruptState))
                        : Failure<MetadataCommitReceipt>(MetadataFailureCode.Conflict, MetadataPhase.Commit);
                }
                var candidate = previous with { TimeFloor = now };
                var artifacts = new HashSet<ArtifactDigest>();
                foreach (var mutation in request.Mutations)
                {
                    activity.Check();
                    candidate = Mutate(candidate, mutation, now, artifacts);
                    if (Interlocked.Exchange(ref failNextWrite, 0) != 0) { throw new MemoryContractFailure(MetadataFailureCode.Capacity); }
                    await observe("mutation.applied");
                }
                ValidateGraph(candidate, request.Mutations, activity);
                await observe("commit.before_decision");
                await observe("M0");
                activity.Check();
                now = Now(candidate);
                Volatile.Write(ref state, previous with { TimeFloor = now });
                if (now >= request.Ticket.Expires.UnixMilliseconds)
                { throw new MemoryContractFailure(MetadataFailureCode.ReconciliationExpired); }
                if (request.LeaseGuard is MetadataOption<MetadataLeaseGuard>.Some guard)
                { RequireOwned(candidate, guard.Value.Resource, guard.Value.Owner, guard.Value.Generation, null, now); }
                foreach (var mutation in request.Mutations)
                {
                    switch (mutation)
                    {
                        case MetadataMutation.AcquireLease acquisition:
                            var acquiredLease = (MetadataWorkLease)candidate.Records[new MetadataSelector.Lease(acquisition.Resource)];
                            candidate = Replace(candidate, acquiredLease with { Acquired = new(now), Expires = new(checked(now + acquisition.TtlSeconds * 1000L)) });
                            break;
                        case MetadataMutation.RenewLease renew:
                            RequireOwned(previous, renew.Resource, renew.Owner, renew.Generation, renew.Revision, now);
                            var currentLease = (MetadataWorkLease)candidate.Records[new MetadataSelector.Lease(renew.Resource)];
                            candidate = Replace(candidate, currentLease with { Acquired = new(now), Expires = new(checked(now + renew.TtlSeconds * 1000L)) });
                            break;
                        case MetadataMutation.ReleaseLease release:
                            RequireOwned(previous, release.Resource, release.Owner, release.Generation, release.Revision, now); break;
                        case MetadataMutation.ConfirmUnreferenced confirm:
                            if (!candidate.Records.TryGetValue(new MetadataSelector.Artifact(confirm.Digest), out var record)
                                || record is not MetadataArtifactState artifact || artifact.Revision != confirm.ReferenceRevision
                                || artifact.LiveReferences != 0)
                            { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
                            break;
                    }
                }
                var targets = request.Mutations.Select(MetadataEncoding.Target).Select(target =>
                    new MetadataTargetRevision(target, candidate.Records.TryGetValue(target, out var record)
                        ? new MetadataOption<MetadataRevision>.Some(record.Revision) : new MetadataOption<MetadataRevision>.None())).ToImmutableArray();
                var references = artifacts.Select(digest =>
                {
                    var artifact = (MetadataArtifactState)candidate.Records[new MetadataSelector.Artifact(digest)];
                    return new MetadataReferenceObservation(digest, artifact.Revision, artifact.LiveReferences);
                }).ToImmutableArray();
                var receipt = new MetadataCommitReceipt(request.Ticket, new(Guid.NewGuid()), targets, references);
                _ = MetadataEncoding.Encode(receipt);
                var committed = candidate with
                {
                    TimeFloor = now,
                    Changes = checked(previous.Changes + 1),
                    Operations = candidate.Operations.SetItem(request.Ticket.Id, operation with { State = 1, Fingerprint = fingerprint, Receipt = receipt })
                };
                activity.CommitDecision();
                Volatile.Write(ref state, committed);
                activity.Committed();
                await observe("M1");
                return Success(receipt);
            }
            finally { writer.Release(); }
        }
        finally
        {
            var cleanupFailed = false;
            foreach (var guard in guards)
            {
                try { await guard.DisposeAsync(); }
                catch (Exception) { diagnostic("metadata.publication_cleanup_failed"); cleanupFailed = true; }
            }
            if (cleanupFailed) { throw new InvalidOperationException("Memory publication cleanup failed."); }
        }
    }
}
