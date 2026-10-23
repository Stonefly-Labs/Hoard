using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;

internal sealed record CrashStamp(string Digest, long Length, Guid Incarnation)
{
    public static CrashStamp From(ArtifactStamp stamp) => new(stamp.Identity.Digest.Hex, stamp.Identity.Length, stamp.Incarnation);
    public ArtifactStamp In(ArtifactStoreIdentity store) => new(store, new ArtifactIdentity(new ArtifactDigest(Digest), Length), Incarnation);
}

internal sealed record CrashStage(ArtifactStagingOwner Owner, string Digest, long Length, Guid Verification, string Handle)
{
    public static CrashStage From(ArtifactStagedWrite staged) => new(staged.Owner, staged.Identity.Digest.Hex,
        staged.Identity.Length, staged.VerifiedCompletion, staged.PrivateHandle);
    public ArtifactStagedWrite ToStaged() => new(Owner, new ArtifactIdentity(new ArtifactDigest(Digest), Length), Verification, Handle);
}

internal sealed record CrashState(Guid Run, string Barrier, ArtifactStoreIdentity Store,
    ArtifactOperationTicket ControlTicket, Guid ControlReceipt, CrashStamp Control,
    ArtifactOperationTicket Ticket, string TargetDigest, long TargetLength,
    CrashStamp? Target = null, Guid? AcknowledgedReceipt = null, CrashStage? Stage = null,
    ArtifactStagingOwner? PriorOwner = null);

internal static class ArtifactCrashScenario
{
    private static readonly byte[] ControlBytes = "acknowledged independent control before crash"u8.ToArray();
    private static readonly byte[] TargetBytes = Enumerable.Range(0, 1048576).Select(index => (byte)(index * 17 + 11)).ToArray();

    public static async Task<int> ExecuteAsync(string[] args)
    {
        var root = Path.GetFullPath(args[1]);
        var record = Path.GetFullPath(args[2]);
        var barrier = args[3];
        var run = Guid.Parse(args[4]);
        if (barrier is not ("B0" or "B1" or "B2" or "B3" or "D0" or "D1"))
        { throw new ArgumentException("Unknown artifact crash boundary."); }
        if (args[0] == "crash") { await CrashAsync(root, record, barrier, run); }
        else { await RecoverAsync(root, record, barrier, run); }
        return 0;
    }

    private static ArtifactCoordinationAuthority Authority(ArtifactStoreIdentity store)
        => new(store, references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));

    private static async Task CrashAsync(string root, string record, string barrier, Guid run)
    {
        var identity = new ArtifactStoreIdentity("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
        var faults = new LocalFaultControls();
        var provider = new LocalArtifactStore(root, controls: faults);
        Need(await provider.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, Authority(identity)), new(), default));
        IArtifactStore store = provider;
        IArtifactMaintenance maintenance = provider;
        var control = await PublishAsync(store, ControlBytes);
        var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(TargetBytes.Length)), new(), default));
        var digest = Convert.ToHexStringLower(SHA256.HashData(TargetBytes));
        var state = new CrashState(run, barrier, identity, control.Ticket, control.ReceiptId,
            CrashStamp.From(control.Stamp), ticket, digest, TargetBytes.LongLength);

        async ValueTask PauseAsync()
        {
            if (barrier is "B0" or "B1")
            {
                var page = Need(await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Staging), new(), default));
                var owner = page.Observations.Single(row => row.OperationId == ticket.Id).Owner;
                state = state with { PriorOwner = ((ArtifactOption<ArtifactStagingOwner>.Some)owner).Value };
            }
            else if (barrier == "B2")
            {
                var page = Need(await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed), new(), default));
                var stamp = page.Observations.Single(row => row.OperationId == ticket.Id).Stamp;
                state = state with { Target = CrashStamp.From(((ArtifactOption<ArtifactStamp>.Some)stamp).Value) };
            }
            Save(record, state);
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                eventName = "barrier",
                pid = Environment.ProcessId,
                runId = run,
                barrier,
                stateSha256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(record))),
                acknowledged = barrier == "B3"
            }));
            await Console.Out.FlushAsync();
            await Task.Delay(TimeSpan.FromMinutes(4));
            throw new TimeoutException("Artifact crash child did not receive its owned parent signal.");
        }

        var point = barrier switch
        {
            "B0" => "stage.prefix",
            "B1" => "stage.verified",
            "B2" => "publish.decided",
            "D0" => "delete.removed",
            "D1" => "delete.reclaimed",
            _ => null
        };
        if (point is not null) { faults.SetObserver(point, PauseAsync); }
        using var source = new MemoryStream(TargetBytes, writable: false);
        var staged = Need(await store.StageAsync(ticket, source, new(), default));
        state = state with { Stage = CrashStage.From(staged) };
        var publication = Need(await store.CommitAsync(staged, new(), default));
        state = state with { Target = CrashStamp.From(publication.Stamp), AcknowledgedReceipt = publication.ReceiptId };
        if (barrier == "B3") { await PauseAsync(); }
        else
        {
            var deletion = Need(await store.ReserveDeleteAsync(new(publication.Stamp), new(), default));
            state = state with { Ticket = deletion, AcknowledgedReceipt = null };
            Need(await store.DeleteAsync(deletion, new(), default));
        }
        throw new InvalidOperationException("Artifact crash child passed its required parent-kill boundary.");
    }

    private static async Task RecoverAsync(string root, string record, string barrier, Guid run)
    {
        var state = JsonSerializer.Deserialize<CrashState>(File.ReadAllBytes(record))
            ?? throw new InvalidOperationException("Artifact crash state is missing.");
        Require(state.Run == run && state.Barrier == barrier, "Artifact crash state belongs to another run.");
        var provider = new LocalArtifactStore(root);
        Need(await provider.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, state.Store,
            Authority(state.Store)), new(), default));
        IArtifactStore store = provider;
        IArtifactMaintenance maintenance = provider;
        try
        {
            var control = (ArtifactResolution.Committed)Need(await store.ReconcileAsync(state.ControlTicket, new(), default));
            Require(control.Receipt.ReceiptId == state.ControlReceipt
                && control.Receipt.Stamp == state.Control.In(state.Store), "Acknowledged control receipt changed.");
            await VerifyReadAsync(store, control.Receipt.Stamp, ControlBytes);
            var ownerFenced = false;
            var reconstructed = false;
            var reclamation = "NotApplicable";
            ArtifactMutationReceipt outcome;
            if (barrier is "B0" or "B1")
            {
                Require(Need(await store.ReconcileAsync(state.Ticket, new(), default)) is ArtifactResolution.Pending,
                    "A stage without decision intent must remain resumable.");
                var absent = await store.OpenReadAsync(new(new ArtifactDigest(state.TargetDigest)), new(), default);
                Require(absent is ArtifactResult<IArtifactReadSession>.Failure { Code: ArtifactFailureCode.NotFound },
                    "An incomplete stage became committed content.");
                var old = state.PriorOwner ?? throw new InvalidOperationException("Prior crash owner is missing.");
                Require(await store.RenewAsync(old, new(), default) is ArtifactResult<ArtifactStagingOwner>.Failure,
                    "Prior process ownership was renewed.");
                Require(await store.AbandonAsync(old, new(), default) is ArtifactResult<ArtifactCleanupReport>.Failure,
                    "Prior process ownership was allowed to abandon.");
                using var fresh = new MemoryStream(TargetBytes, writable: false);
                var staged = Need(await store.StageAsync(state.Ticket, fresh, new(), default));
                Require(staged.Owner.Generation > old.Generation && staged.Owner.SessionId != old.SessionId,
                    "Restart reused a staging generation.");
                var oldStaged = new ArtifactStagedWrite(old, staged.Identity, Guid.NewGuid(), old.OwnerId.ToString("N"));
                Require(await store.CommitAsync(oldStaged, new(), default) is ArtifactResult<ArtifactMutationReceipt>.Failure,
                    "An old generation was allowed to commit.");
                var cleanup = Need(await maintenance.CleanupAsync(new(state.Store,
                    [new ArtifactCleanupTarget.AbandonedStaging(old)]), new(), default));
                Require(cleanup.Conflicted == 1 && cleanup.ReclaimedBytes == 0, "Stale cleanup reclaimed new staging.");
                outcome = Need(await store.CommitAsync(staged, new(), default));
                ownerFenced = true;
                reconstructed = true;
            }
            else if (barrier is "B2" or "B3")
            {
                var resolved = (ArtifactResolution.Committed)Need(await store.ReconcileAsync(state.Ticket, new(), default));
                outcome = resolved.Receipt;
                Require(outcome.Stamp == state.Target!.In(state.Store), "Recovery selected another incarnation.");
                if (state.AcknowledgedReceipt is { } acknowledged)
                { Require(outcome.ReceiptId == acknowledged, "Acknowledged publication receipt changed."); }
                Require(Need(await store.CommitAsync(state.Stage!.ToStaged(), new(), default)) == outcome,
                    "Exact publication retry produced another receipt.");
            }
            else
            {
                outcome = ((ArtifactResolution.Removed)Need(await store.ReconcileAsync(state.Ticket, new(), default))).Receipt;
                reclamation = outcome.Reclamation.ToString();
                Require(outcome.Stamp == state.Target!.In(state.Store), "Recovery removed another incarnation.");
                Require(outcome.Reclamation == (barrier == "D0" ? ArtifactReclamation.Pending : ArtifactReclamation.Reclaimed),
                    "Durable reclamation progress was not reconciled.");
                var absent = await store.OpenReadAsync(new(outcome.Stamp.Identity.Digest), new(), default);
                Require(absent is ArtifactResult<IArtifactReadSession>.Failure { Code: ArtifactFailureCode.NotFound },
                    "Logical deletion was forgotten.");
                Require(Need(await store.DeleteAsync(state.Ticket, new(), default)).ReceiptId == outcome.ReceiptId,
                    "Exact deletion retry produced another receipt.");
                var recreated = await PublishAsync(store, TargetBytes);
                Require(recreated.Stamp.Incarnation != outcome.Stamp.Incarnation, "Recreation reused the old incarnation.");
                Need(await maintenance.CleanupAsync(new(state.Store,
                    [new ArtifactCleanupTarget.RemovedIncarnation(outcome.Stamp)]), new(), default));
                Need(await store.DeleteAsync(state.Ticket, new(), default));
                await VerifyReadAsync(store, recreated.Stamp, TargetBytes);
                ownerFenced = true;
            }
            if (outcome.Visibility == ArtifactVisibility.Committed)
            { await VerifyReadAsync(store, outcome.Stamp, TargetBytes); }
            var repeated = Need(await store.ReconcileAsync(state.Ticket, new(), default));
            if (state.Stage is { } previous)
            {
                Require(await store.RenewAsync(previous.Owner, new(), default) is ArtifactResult<ArtifactStagingOwner>.Failure,
                    "A prior staging owner was revived after restart.");
                Require(await store.AbandonAsync(previous.Owner, new(), default) is ArtifactResult<ArtifactCleanupReport>.Failure,
                    "A prior staging owner was allowed to abandon after restart.");
                ownerFenced = true;
            }
            var inventory = Need(await maintenance.ObserveAsync(new(state.Store, ArtifactRecoveryKind.Committed), new(), default));
            Require(inventory.Observations.Count(row => row.Stamp is ArtifactOption<ArtifactStamp>.Some stamp
                && stamp.Value.Identity.Digest.Hex == state.TargetDigest) == 1, "Recovery produced duplicate logical publication.");
            var repeatedReceipt = repeated switch
            {
                ArtifactResolution.Committed committed => committed.Receipt,
                ArtifactResolution.Removed removed => removed.Receipt,
                _ => throw new InvalidOperationException("Recovered ticket lost its decided outcome.")
            };
            Require(outcome.ReceiptId == repeatedReceipt.ReceiptId && outcome.Stamp == repeatedReceipt.Stamp
                && outcome.Outcome == repeatedReceipt.Outcome, "Recovered logical receipt was not stable.");
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                eventName = "recovered",
                provider = "local",
                qualification = false,
                pid = Environment.ProcessId,
                runId = run,
                barrier,
                controlReadback = true,
                controlReceipt = true,
                exactReceipt = true,
                contentReadback = true,
                ownerFenced,
                reconstructed,
                reclamation,
                noDuplicateEffect = true,
                contentSha256 = Convert.ToHexStringLower(SHA256.HashData(TargetBytes)),
                contentLength = TargetBytes.LongLength,
                controlSha256 = Convert.ToHexStringLower(SHA256.HashData(ControlBytes)),
                controlLength = ControlBytes.LongLength,
                outcome = outcome.Outcome.ToString(),
                receiptId = outcome.ReceiptId
            }));
        }
        finally { Need(await provider.StopAsync(new(), default)); }
    }

    private static async Task<ArtifactMutationReceipt> PublishAsync(IArtifactStore store, byte[] bytes)
    {
        var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(bytes.Length)), new(), default));
        using var source = new MemoryStream(bytes, writable: false);
        var stage = Need(await store.StageAsync(ticket, source, new(), default));
        return Need(await store.CommitAsync(stage, new(), default));
    }

    private static async Task VerifyReadAsync(IArtifactStore store, ArtifactStamp stamp, byte[] expected)
    {
        await using var session = Need(await store.OpenReadAsync(new(stamp.Identity.Digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        using var destination = new MemoryStream();
        var complete = Need(await session.CopyToAsync(destination, new(), default));
        Require(complete.Length == expected.Length && destination.ToArray().AsSpan().SequenceEqual(expected),
            "Recovered content readback did not match its acknowledged bytes.");
    }

    private static void Save(string path, CrashState state)
    {
        var bytes = JsonSerializer.SerializeToUtf8Bytes(state);
        Require(bytes.Length <= 16384, "Artifact crash state exceeded its bound.");
        using var file = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read);
        file.Write(bytes);
        file.Flush(flushToDisk: true);
    }

    private static T Need<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failure
                ? "Artifact crash operation failed: " + failure.Code : "Artifact crash operation failed.");
    private static void Require(bool condition, string message)
    { if (!condition) { throw new InvalidOperationException(message); } }
}
