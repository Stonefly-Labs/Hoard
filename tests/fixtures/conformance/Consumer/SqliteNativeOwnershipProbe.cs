using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class SqliteNativeOwnershipProbe
{
    internal static async Task<int> RunAsync(string[] args)
    {
        var inputsSha256 = ConformanceBindingDeclaration.Hash(args[5]);
        // Deliberately retained until exact-child containment; neither object may be disposed early.
        var resources = ConformanceResourceAllocator.Open(args[2], args[3]);
        var session = await new SqliteBinding(args[4]).CreateSessionAsync(new(
            Guid.NewGuid(), "sqlite-native-noncooperation", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer()), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var (_, package) = await Seed(session.Store, default);
        var entry = Entry(package);
        var ticket = await Ticket(session.Store, default);
        var request = Batch(ticket, Publish(session.Authority, entry));
        await session.Faults.ArmAsync(ConformanceFault.NativeNonCooperation, default);
        var committing = session.Store.CommitAsync(request, new(TimeSpan.FromSeconds(1)), default).AsTask();
        await session.Faults.WaitForBoundaryAsync(ConformanceFault.NativeNonCooperation, default);
        var boundary = await session.Faults.ObserveAsync(ConformanceFault.NativeNonCooperation, default);
        var guardsAtBoundary = session.Authority.ActiveGuards;
        var failure = await committing is MetadataResult<MetadataCommitReceipt>.Failure failed
            ? failed : throw new InvalidOperationException("ProofMismatch");
        var failedTicket = failure.Ticket is MetadataOption<MetadataOperationTicket>.Some some
            ? some.Value : throw new InvalidOperationException("ProofMismatch");
        var guardsAfterDeadline = session.Authority.ActiveGuards;
        var disposeCode = "None";
        try { await session.DisposeAsync(); }
        catch (InvalidOperationException) when (session.Faults.Counters.IncompleteCleanups == 1)
        { disposeCode = "CleanupIncomplete"; }
        var cleanup = await session.ObserveCleanupAsync(default);
        var admission = await session.Store.ReserveOperationAsync(new(), default)
            is MetadataResult<MetadataOperationTicket>.Failure denied
            ? denied.Code.ToString() : "None";
        var settlement = ((SqliteMetadataStore)session.Store).ObserveLifetimeSettlementForTest();
        var ledger = resources.ObserveLedger();
        using (var output = new FileStream(args[1], FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            JsonSerializer.Serialize(output, new
            {
                schemaVersion = 1,
                inputsSha256,
                childPid = Environment.ProcessId,
                boundaryObservations = boundary.ObservationCount,
                guards = new[] { guardsAtBoundary, guardsAfterDeadline, session.Authority.ActiveGuards },
                commitCode = failure.Code.ToString(),
                commitPhase = failure.Phase.ToString(),
                commitRetry = failure.Retry.ToString(),
                ticketSha256 = Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(ticket))),
                failureTicketSha256 = Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(failedTicket))),
                disposeCode,
                incompleteCleanups = session.Faults.Counters.IncompleteCleanups,
                admissionCode = admission,
                settlementCompleted = settlement.IsCompleted,
                cleanupState = cleanup.State.ToString(),
                resourceIds = cleanup.ResourceIds,
                ledgerStates = ledger.Select(item => item.Observation.State.ToString()).ToArray()
            });
        }
        await Task.Delay(Timeout.InfiniteTimeSpan);
        throw new InvalidOperationException("EvidenceIncomplete");
    }
}
