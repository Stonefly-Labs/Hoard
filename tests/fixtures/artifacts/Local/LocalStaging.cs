using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(intent);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Reserve, options.Deadline, ct, token =>
        {
            var expectation = intent.Expectations;
            if (expectation.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some checksum)
            {
                if (checksum.Value.Algorithm != "sha512") { throw new LocalStateException(ArtifactFailureCode.Unsupported); }
                if (checksum.Value.Digest.Length != 64) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            }
            lock (stateSync)
            {
                token.ThrowIfCancellationRequested();
                if (expectation.ByteCap > Limits.ArtifactBytes) { throw new LocalStateException(ArtifactFailureCode.LimitExceeded); }
                RetireExpiredTickets(token);
                if (operations.Count >= Limits.LiveTickets || expectation.ByteCap > Limits.StagingBytes - reserved)
                { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                var issued = Now();
                var operation = new LocalOperation
                {
                    Id = Guid.NewGuid(),
                    Issued = issued,
                    Expires = issued.AddHours(24),
                    Cap = expectation.ByteCap,
                    Kind = ArtifactOperationKind.Write,
                    ExpectedDigest = expectation.Sha256 is ArtifactOption<ArtifactDigest>.Some hash ? hash.Value.Hex : null,
                    ExpectedLength = expectation.ExactLength is ArtifactOption<long>.Some length ? length.Value : null,
                    ExpectedChecksum = expectation.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some additional
                        ? Convert.ToHexStringLower(additional.Value.Digest.AsSpan()) : null
                };
                operation.Fingerprint = Fingerprint(new { operation.Cap, operation.ExpectedDigest, operation.ExpectedLength, operation.ExpectedChecksum });
                Save(operation);
                if (!operations.TryAdd(operation.Id, operation)) { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                reserved = checked(reserved + operation.Cap);
                return Task.FromResult(Ticket(operation));
            }
        }, undelivered: DiscardUndeliveredTicketAsync);
    }

    private ValueTask DiscardUndeliveredTicketAsync(ArtifactOperationTicket ticket)
    {
        lock (stateSync)
        {
            if (!operations.TryGetValue(ticket.Id, out var operation) || Ticket(operation) != ticket
                || operation.State != "reserved") { throw new LocalStateException(ArtifactFailureCode.Conflict); }
            ReleaseStaging(operation);
            File.Delete(ownership!.RecordPath("tickets", operation.Id.ToString("N")));
            ReleaseHistoryDependency(operation.Id);
            operations.TryRemove(operation.Id, out _);
            indexedIncarnations.Remove(operation.Id);
        }
        return ValueTask.CompletedTask;
    }

    private void RetireExpiredTickets(CancellationToken token)
    {
        var now = Now();
        var retire = operations.Count >= Limits.LiveTickets;
        var candidates = Math.Min(100, ticketCandidates.Count);
        for (var index = 0; index < candidates; index++)
        {
            var id = ticketCandidates.Dequeue();
            try
            {
                token.ThrowIfCancellationRequested();
                HistoryCandidate("tickets", id.ToString("N"));
                if (!operations.TryGetValue(id, out var expired)) { continue; }
                if (now < expired.Expires || expired.State == "deciding" || TicketInUse(id)) { continue; }
                if (expired.Content is { } content && decisions.TryGetValue(content.Digest, out var anchored)
                    && anchored.Operation == id && anchored.ReconcileUntil is null)
                { continue; }
                if (expired.State is "reserved" or "staging" or "verified")
                {
                    expired.State = "notcommitted";
                    Save(expired);
                }
                ReleaseStaging(expired);
                ReleaseHistoryDependency(id);
                if (!retire) { continue; }
                ownership!.PersistTime();
                File.Delete(ownership.RecordPath("tickets", id.ToString("N")));
                operations.TryRemove(id, out _);
                indexedIncarnations.Remove(id);
                inventoryRevision = checked(inventoryRevision + 1);
            }
            finally { if (operations.ContainsKey(id)) { ticketCandidates.Enqueue(id); } }
        }
        CompactReclaimedHistory(now, token);
    }

    private void CompactReclaimedHistory(DateTimeOffset now, CancellationToken token)
    {
        bool Retirable(LocalDecision decision) => decision is { Removed: true, Reclaimed: true, ReconcileUntil: { } expiry }
            && now >= expiry && !historyDependents.ContainsKey(decision.Content.Incarnation);

        var remaining = 100;
        var candidates = Math.Min(100, reclamationCandidates.Count);
        for (var index = 0; index < candidates && remaining > 0; index++)
        {
            token.ThrowIfCancellationRequested();
            var node = reclamationCandidates.First!;
            reclamationCandidates.RemoveFirst();
            reclamationCandidates.AddLast(node);
            HistoryCandidate("reclamation", node.Value.ToString("N"));
            var retired = removedContent[node.Value];
            if (!Retirable(retired)) { continue; }
            ownership!.PersistTime();
            File.Delete(ownership.RecordPath("reclamation", retired.Content.Incarnation.ToString("N")));
            ForgetReclamation(retired.Content.Incarnation);
            if (decisions.TryGetValue(retired.Content.Digest, out var current)
                && current.Content == retired.Content && Retirable(current))
            {
                File.Delete(ownership.RecordPath("decisions", current.Content.Digest));
                ForgetDecision(current.Content.Digest);
            }
            inventoryRevision = checked(inventoryRevision + 1);
            remaining--;
        }
        candidates = Math.Min(100, decisionCandidates.Count);
        for (var index = 0; index < candidates && remaining > 0; index++)
        {
            token.ThrowIfCancellationRequested();
            var node = decisionCandidates.First!;
            decisionCandidates.RemoveFirst();
            decisionCandidates.AddLast(node);
            HistoryCandidate("decisions", node.Value);
            var orphan = decisions[node.Value];
            if (removedContent.ContainsKey(orphan.Content.Incarnation) || !Retirable(orphan)) { continue; }
            ownership!.PersistTime();
            File.Delete(ownership.RecordPath("decisions", orphan.Content.Digest));
            ForgetDecision(orphan.Content.Digest);
            inventoryRevision = checked(inventoryRevision + 1);
            remaining--;
        }
    }

    private void HistoryCandidate(string kind, string id) => faults.BeforeHistoryCandidate?.Invoke(kind, id);

    public ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Stage, options.Deadline, ct, async token =>
        {
            using var slot = await AdmitAsync(token);
            LocalOperation operation;
            ArtifactStagingOwner owner;
            lock (stateSync)
            {
                operation = Find(ticket, ArtifactOperationKind.Write);
                if (!source.CanRead) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                if (operation.State != "reserved" || operation.Generation == long.MaxValue)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                if (operation.ReservationReleased)
                {
                    if (operation.Cap > Limits.StagingBytes - reserved) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                    reserved = checked(reserved + operation.Cap);
                    operation.ReservationReleased = false;
                }
                if (operation.Owner != Guid.Empty) { File.Delete(StagePath(operation)); }
                operation.Session = ownership!.State.SessionId;
                operation.Owner = Guid.NewGuid();
                operation.Generation++;
                operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                operation.State = "staging";
                Save(operation);
                owner = Owner(operation);
            }
            try
            {
                await using var output = new FileStream(StagePath(operation), FileMode.CreateNew, FileAccess.Write,
                    FileShare.None, 1, FileOptions.Asynchronous | FileOptions.SequentialScan);
                using var sha256 = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                using var sha512 = operation.ExpectedChecksum is null ? null : IncrementalHash.CreateHash(HashAlgorithmName.SHA512);
                var buffer = new byte[Limits.CopyBufferBytes];
                long length = 0;
                var renewal = time.GetTimestamp();
                while (true)
                {
                    using var inactivity = CancellationTokenSource.CreateLinkedTokenSource(token);
                    inactivity.CancelAfter(options.Inactivity);
                    var count = await source.ReadAsync(buffer, inactivity.Token);
                    token.ThrowIfCancellationRequested();
                    lock (stateSync)
                    {
                        CheckOwner(operation, owner);
                        if (count > operation.Cap - length) { throw new LocalStateException(ArtifactFailureCode.LimitExceeded); }
                        if (time.GetElapsedTime(renewal) >= configuration!.Ownership.Renewal)
                        {
                            operation.OwnerExpires = Now().Add(configuration.Ownership.Ttl);
                            owner = Owner(operation);
                            Save(operation);
                            renewal = time.GetTimestamp();
                        }
                    }
                    if (count == 0) { break; }
                    await output.WriteAsync(buffer.AsMemory(0, count), token);
                    sha256.AppendData(buffer, 0, count);
                    sha512?.AppendData(buffer, 0, count);
                    length = checked(length + count);
                    if (length == count) { await faults.ObserveAsync("stage.prefix"); }
                }
                var digest = Convert.ToHexStringLower(sha256.GetHashAndReset());
                if (operation.ExpectedDigest is { } expected && digest != expected
                    || operation.ExpectedLength is { } exact && length != exact
                    || operation.ExpectedChecksum is { } extra && Convert.ToHexStringLower(sha512!.GetHashAndReset()) != extra)
                { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                await output.FlushAsync(token);
                output.Flush(flushToDisk: true);
                lock (stateSync)
                {
                    token.ThrowIfCancellationRequested();
                    CheckOwner(operation, owner);
                    operation.Content = new(digest, length, Guid.NewGuid());
                    operation.Verified = Guid.NewGuid();
                    operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                    operation.State = "verified";
                    Save(operation);
                }
                await faults.ObserveAsync("stage.verified");
                token.ThrowIfCancellationRequested();
                lock (stateSync) { return Staged(operation); }
            }
            catch
            {
                lock (stateSync)
                {
                    operation.State = "notcommitted";
                    Save(operation);
                    ReleaseStaging(operation);
                }
                throw;
            }
        }, ticket, undelivered: staged =>
        {
            lock (stateSync)
            {
                if (!operations.TryGetValue(staged.Owner.Ticket.Id, out var operation)
                    || Ticket(operation) != staged.Owner.Ticket || Owner(operation) != staged.Owner
                    || operation.Session != ownership!.State.SessionId || Staged(operation) != staged
                    || operation.State is not ("verified" or "notcommitted"))
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                operation.State = "notcommitted";
                Save(operation);
                ReleaseStaging(operation);
            }
            return ValueTask.CompletedTask;
        });
    }

    private void ReleaseStaging(LocalOperation operation)
    {
        if (operation.Owner != Guid.Empty) { File.Delete(StagePath(operation)); }
        if (!operation.ReservationReleased)
        {
            reserved = checked(reserved - operation.Cap);
            operation.ReservationReleased = true;
            Save(operation);
        }
    }

    public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Maintenance, options.Deadline, ct, token =>
        {
            lock (stateSync)
            {
                var operation = Find(owner.Ticket, ArtifactOperationKind.Write);
                CheckOwner(operation, owner, requireVerified: true);
                token.ThrowIfCancellationRequested();
                operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                Save(operation);
                return Task.FromResult(Owner(operation));
            }
        }, owner.Ticket);
    }
}
