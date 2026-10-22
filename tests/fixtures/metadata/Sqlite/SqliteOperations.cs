using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

internal sealed class SqliteContractFailure(MetadataFailureCode code) : Exception("Metadata contract rejected work.")
{
    public MetadataFailureCode Code { get; } = code;
}

public sealed partial class SqliteMetadataStore
{
    private sealed record Operation(MetadataOperationTicket Ticket, int State, byte[]? Fingerprint, MetadataCommitReceipt? Receipt);

    private Operation? ReadOperation(MetadataOperationTicket ticket)
    {
        MetadataEncoding.ValidateTicket(ticket);
        if (ticket.Epoch != epoch) { return null; }
        using var select = new SqliteStatement(Database,
            "SELECT epoch,issued,expires,state,fingerprint,receipt FROM metadata_operations WHERE id=?1", IdBytes(ticket.Id));
        if (!select.Step()) { return null; }
        var stored = new MetadataOperationTicket(new(new Guid(select.Bytes(0), bigEndian: true)), ticket.Id,
            new(select.Number(1)), new(select.Number(2)));
        if (stored != ticket) { return null; }
        return new(stored, checked((int)select.Number(3)), select.IsNull(4) ? null : select.Bytes(4),
            select.IsNull(5) ? null : JsonSerializer.Deserialize<MetadataCommitReceipt>(select.Text(5), Json)
                ?? throw new SqliteNativeFailure(11));
    }

    private async ValueTask<MetadataResult<MetadataOperationTicket>> ReserveCoreAsync(SqliteWorkBudget budget)
    {
        await BeginAsync(budget);
        try
        {
            var now = EffectiveNow();
            SqliteStatement.Execute(Database,
                "DELETE FROM metadata_operations WHERE id IN(SELECT id FROM metadata_operations WHERE expires<=?1 ORDER BY expires,id LIMIT 100)", now);
            using (var count = new SqliteStatement(Database, "SELECT count(*) FROM metadata_operations"))
            {
                if (!count.Step()) { throw new SqliteNativeFailure(11); }
                if (count.Number(0) >= 100000) { throw new SqliteContractFailure(MetadataFailureCode.Capacity); }
            }
            var ticket = new MetadataOperationTicket(epoch!, new(Guid.NewGuid()), new(now), new(checked(now + 86400000)));
            SqliteStatement.Execute(Database,
                "INSERT INTO metadata_operations(id,epoch,issued,expires,state) VALUES(?1,?2,?3,?4,0)",
                IdBytes(ticket.Id), IdBytes(ticket.Epoch), now, ticket.Expires.UnixMilliseconds);
            await observe("reserve.before_commit");
            budget.Check();
            SqliteStatement.Execute(Database, "COMMIT");
            return Ok(ticket);
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
    }

    private async ValueTask<MetadataResult<MetadataResolution>> ReconcileCoreAsync(MetadataOperationTicket ticket, SqliteWorkBudget budget)
    {
        MetadataEncoding.ValidateTicket(ticket);
        await BeginAsync(budget);
        try
        {
            var now = EffectiveNow();
            var operation = ReadOperation(ticket);
            if (operation is null || now >= ticket.Expires.UnixMilliseconds)
            {
                SqliteStatement.Execute(Database, "COMMIT");
                return Fail<MetadataResolution>(MetadataFailureCode.ReconciliationExpired, MetadataPhase.Reconcile);
            }
            if (operation.State == 1)
            {
                SqliteStatement.Execute(Database, "COMMIT");
                return Ok<MetadataResolution>(new MetadataResolution.Committed(operation.Receipt ?? throw new SqliteNativeFailure(11)));
            }
            await observe("reconcile.before_decision");
            budget.Check();
            if (!budget.TryCommitDecision()) { budget.Check(); throw new SqliteBudgetFailure(false); }
            SqliteStatement.Execute(Database, "UPDATE metadata_operations SET state=2 WHERE id=?1 AND state=0", IdBytes(ticket.Id));
            SqliteStatement.Execute(Database, "COMMIT");
            budget.Committed();
            return Ok<MetadataResolution>(new MetadataResolution.NotCommitted(ticket));
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
    }

    private async ValueTask<MetadataResult<MetadataCommitReceipt>> CommitCoreAsync(MetadataMutationBatch request, SqliteWorkBudget budget)
    {
        _ = MetadataEncoding.Encode(request);
        var fingerprint = MetadataEncoding.Fingerprint(request).ToArray();
        Operation? initial;
        long initialNow;
        await BeginAsync(budget);
        try
        {
            initialNow = EffectiveNow();
            initial = ReadOperation(request.Ticket);
            SqliteStatement.Execute(Database, "COMMIT");
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
        if (initial is null || initialNow >= request.Ticket.Expires.UnixMilliseconds)
        { return Fail<MetadataCommitReceipt>(MetadataFailureCode.ReconciliationExpired, MetadataPhase.Commit); }
        if (initial.State == 1)
        {
            return initial.Fingerprint is not null && initial.Fingerprint.AsSpan().SequenceEqual(fingerprint)
                ? Ok(initial.Receipt ?? throw new SqliteNativeFailure(11))
                : Fail<MetadataCommitReceipt>(MetadataFailureCode.Conflict, MetadataPhase.Commit);
        }
        if (initial.State == 2) { return Fail<MetadataCommitReceipt>(MetadataFailureCode.Conflict, MetadataPhase.Commit); }
        var guards = new List<IMetadataPublicationGuard>();
        try
        {
            var publications = request.Mutations.OfType<MetadataMutation.PublishCacheEntry>()
                .GroupBy(item => item.Record.Digest).ToArray();
            foreach (var group in publications)
            {
                budget.Check();
                var expected = group.First();
                if (group.Any(item => item.Record.Length != expected.Record.Length))
                { return Fail<MetadataCommitReceipt>(MetadataFailureCode.InvalidInput, MetadataPhase.Publication); }
                await observe("publication.acquire");
                var result = await authority.AcquireAsync(expected.Evidence, new(budget.Remaining), CancellationToken.None);
                if (result is not MetadataResult<IMetadataPublicationGuard>.Success acquired)
                {
                    return result is MetadataResult<IMetadataPublicationGuard>.Failure rejected
                        ? Fail<MetadataCommitReceipt>(rejected.Code, MetadataPhase.Publication)
                        : Fail<MetadataCommitReceipt>(MetadataFailureCode.InternalFailure, MetadataPhase.Publication);
                }
                guards.Add(acquired.Value);
                if (acquired.Value.Artifact is not { } artifact || artifact.Digest != expected.Record.Digest || artifact.Length != expected.Record.Length)
                { return Fail<MetadataCommitReceipt>(MetadataFailureCode.InvalidInput, MetadataPhase.Publication); }
            }
            budget.Check();
            await BeginAsync(budget);
            try
            {
                var now = EffectiveNow();
                var operation = ReadOperation(request.Ticket);
                if (operation is null || now >= request.Ticket.Expires.UnixMilliseconds)
                {
                    SqliteStatement.Execute(Database, "COMMIT");
                    return Fail<MetadataCommitReceipt>(MetadataFailureCode.ReconciliationExpired, MetadataPhase.Commit);
                }
                if (operation.State != 0)
                {
                    SqliteStatement.Execute(Database, "COMMIT");
                    return operation.State == 1 && operation.Fingerprint is not null && operation.Fingerprint.AsSpan().SequenceEqual(fingerprint)
                        ? Ok(operation.Receipt ?? throw new SqliteNativeFailure(11))
                        : Fail<MetadataCommitReceipt>(MetadataFailureCode.Conflict, MetadataPhase.Commit);
                }
                SqliteStatement.Execute(Database, "SAVEPOINT candidate");
                var observedNow = now;
                try
                {
                    var touchedArtifacts = new HashSet<ArtifactDigest>();
                    var originalLeases = new Dictionary<CanonicalText, MetadataWorkLease>();
                    foreach (var mutation in request.Mutations)
                    {
                        budget.Check();
                        if (mutation is MetadataMutation.RenewLease renewal)
                        { originalLeases.Add(renewal.Resource, OwnedLease(renewal.Resource, renewal.Owner, renewal.Generation, renewal.Revision, now)); }
                        if (mutation is MetadataMutation.ReleaseLease release)
                        { originalLeases.Add(release.Resource, OwnedLease(release.Resource, release.Owner, release.Generation, release.Revision, now)); }
                        Apply(mutation, now, touchedArtifacts);
                        if (Interlocked.Exchange(ref failNextWrite, 0) != 0) { throw new SqliteNativeFailure(13); }
                        await observe("mutation.applied");
                    }
                    foreach (var digest in touchedArtifacts) { UpdateReferenceCount(digest); }
                    foreach (var mutation in request.Mutations) { CheckFinalGraph(mutation); }
                    await observe("commit.before_decision");
                    budget.Check();
                    now = EffectiveNow();
                    observedNow = now;
                    CheckLeaseGuard(request.LeaseGuard, now);
                    foreach (var mutation in request.Mutations.OfType<MetadataMutation.ConfirmUnreferenced>())
                    {
                        if (Get(new MetadataSelector.Artifact(mutation.Digest)) is not MetadataArtifactState artifact
                            || artifact.Revision != mutation.ReferenceRevision || artifact.LiveReferences != 0)
                        { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
                    }
                    var revisions = request.Mutations.Select(mutation =>
                    {
                        var target = MetadataEncoding.Target(mutation);
                        MetadataOption<MetadataRevision> revision = Get(target) is { } record
                            ? new MetadataOption<MetadataRevision>.Some(record.Revision) : new MetadataOption<MetadataRevision>.None();
                        return new MetadataTargetRevision(target, revision);
                    }).ToImmutableArray();
                    var references = touchedArtifacts.Select(digest =>
                    {
                        var artifact = (MetadataArtifactState)(Get(new MetadataSelector.Artifact(digest)) ?? throw new SqliteNativeFailure(11));
                        return new MetadataReferenceObservation(digest, artifact.Revision, artifact.LiveReferences);
                    }).ToImmutableArray();
                    var receipt = new MetadataCommitReceipt(request.Ticket, new(Guid.NewGuid()), revisions, references);
                    _ = MetadataEncoding.Encode(receipt);
                    SqliteStatement.Execute(Database, "UPDATE metadata_operations SET state=1,fingerprint=?1,receipt=?2 WHERE id=?3",
                        fingerprint, JsonSerializer.Serialize(receipt, Json), IdBytes(request.Ticket.Id));
                    SqliteStatement.Execute(Database, "UPDATE metadata_schema SET change_number=change_number+1 WHERE singleton=1");
                    await observe("M0");
                    budget.Check();
                    now = EffectiveNow();
                    observedNow = now;
                    if (now >= request.Ticket.Expires.UnixMilliseconds)
                    { throw new SqliteContractFailure(MetadataFailureCode.ReconciliationExpired); }
                    CheckLeaseGuard(request.LeaseGuard, now);
                    foreach (var lease in originalLeases.Values)
                    {
                        if (now >= lease.Expires.UnixMilliseconds) { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
                    }
                    foreach (var mutation in request.Mutations)
                    {
                        var leaseChange = mutation switch
                        {
                            MetadataMutation.AcquireLease acquisition => (acquisition.Resource, acquisition.TtlSeconds),
                            MetadataMutation.RenewLease renewal => (renewal.Resource, renewal.TtlSeconds),
                            _ => ((CanonicalText?)null, 0)
                        };
                        if (leaseChange.Item1 is not null)
                        {
                            var lease = Get(new MetadataSelector.Lease(leaseChange.Item1)) as MetadataWorkLease ?? throw new SqliteNativeFailure(11);
                            Put(lease with { Acquired = new(now), Expires = new(checked(now + leaseChange.Item2 * 1000L)) });
                        }
                    }
                    if (!budget.TryCommitDecision()) { budget.Check(); throw new SqliteBudgetFailure(false); }
                    SqliteStatement.Execute(Database, "COMMIT");
                    budget.Committed();
                    await observe("M1");
                    return Ok(receipt);
                }
                catch (SqliteContractFailure rejection)
                {
                    SqliteStatement.Execute(Database, "ROLLBACK TO candidate");
                    SqliteStatement.Execute(Database, "RELEASE candidate");
                    SqliteStatement.Execute(Database, "UPDATE metadata_schema SET time_floor=max(time_floor,?1) WHERE singleton=1", observedNow);
                    SqliteStatement.Execute(Database, "COMMIT");
                    return Fail<MetadataCommitReceipt>(rejection.Code, MetadataPhase.Commit);
                }
            }
            finally
            {
                if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
            }
        }
        finally
        {
            var cleanupFailed = false;
            foreach (var guard in guards)
            {
                try { await guard.DisposeAsync(); }
                catch (Exception) { diagnostic("metadata.publication_cleanup_failed"); cleanupFailed = true; }
            }
            if (cleanupFailed) { throw new InvalidOperationException("Metadata publication cleanup failed."); }
        }
    }

    private long ReadTimeFloor()
    {
        using var select = new SqliteStatement(Database, "SELECT time_floor FROM metadata_schema WHERE singleton=1");
        if (!select.Step()) { throw new SqliteNativeFailure(11); }
        return select.Number(0);
    }
}
