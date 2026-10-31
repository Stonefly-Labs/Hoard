using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;

internal static class ArtifactCrashScenario
{
    public static async Task<int> ExecuteAsync(string[] args)
    {
        var root = Path.GetFullPath(args[1]);
        var record = Path.GetFullPath(args[2]);
        var barrier = args[3];
        var run = Guid.Parse(args[4]);
        if (barrier is not ("B0" or "B1" or "B2" or "B3" or "D0" or "D1"))
        { throw new ArgumentException("Unknown artifact crash boundary."); }
        var safeEvents = Environment.GetEnvironmentVariable("HOARD_CONFORMANCE_SAFE_EVENTS") switch
        {
            null => false,
            "1" => true,
            _ => throw new ArgumentException("Invalid artifact recovery event mode.")
        };
        if (args[0] == "crash") { await CrashAsync(root, record, barrier, run, safeEvents); }
        else { await RecoverAsync(root, record, barrier, run, safeEvents); }
        return 0;
    }

    private static void Emit(bool safeEvents, string legacy, int? barrier = null) =>
        Console.WriteLine(safeEvents ? JsonSerializer.Serialize(new
        {
            @event = barrier is null ? "test" : "barrier",
            code = "None",
            value = barrier ?? 1
        }) : legacy);

    private static ArtifactCoordinationAuthority Authority(ArtifactStoreIdentity store)
        => new(store, references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));

    private static async Task CrashAsync(string root, string record, string barrier, Guid run, bool safeEvents)
    {
        var identity = new ArtifactStoreIdentity("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
        var faults = new LocalFaultControls();
        var provider = new LocalArtifactStore(root, controls: faults);
        Need(await provider.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, Authority(identity)), new(), default));
        await ArtifactCrashAssertions.CrashAsync(provider, provider, identity, barrier, run, async state =>
        {
            Save(record, state);
            var value = barrier switch
            {
                "B0" => 40,
                "B1" => 41,
                "B2" => 42,
                "B3" => 43,
                "D0" => 44,
                "D1" => 45,
                _ => throw new ArgumentException("Unknown artifact crash boundary.")
            };
            Emit(safeEvents, JsonSerializer.Serialize(new
            {
                eventName = "barrier",
                pid = Environment.ProcessId,
                runId = run,
                barrier,
                stateSha256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(record))),
                acknowledged = barrier == "B3"
            }), value);
            await Console.Out.FlushAsync();
            await Task.Delay(TimeSpan.FromMinutes(4));
            throw new TimeoutException("Artifact crash child did not receive its owned parent signal.");
        }, (point, callback) =>
        {
            var boundary = point switch
            {
                ArtifactCrashPoint.StagePrefix => "stage.prefix",
                ArtifactCrashPoint.StageVerified => "stage.verified",
                ArtifactCrashPoint.PublicationSelected => "publish.decided",
                ArtifactCrashPoint.DeleteRemoved => "delete.removed",
                ArtifactCrashPoint.DeleteReclaimed => "delete.reclaimed",
                _ => throw new ArgumentException("Unknown artifact crash boundary.")
            };
            faults.SetObserver(boundary, callback);
            return ValueTask.FromResult<IAsyncDisposable>(new Registration(faults, boundary));
        });
    }

    private static async Task RecoverAsync(string root, string record, string barrier, Guid run, bool safeEvents)
    {
        var state = JsonSerializer.Deserialize<ArtifactCrashState>(File.ReadAllBytes(record))
            ?? throw new InvalidOperationException("Artifact crash state is missing.");
        Require(state.Run == run && state.Barrier == barrier, "Artifact crash state belongs to another run.");
        var provider = new LocalArtifactStore(root);
        Need(await provider.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, state.Store,
            Authority(state.Store)), new(), default));
        try
        {
            var observed = await ArtifactCrashAssertions.RecoverAsync(provider, provider, state, barrier, run);
            Emit(safeEvents, JsonSerializer.Serialize(new
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
                ownerFenced = observed.OwnerFenced,
                reconstructed = observed.Reconstructed,
                reclamation = observed.Reclamation,
                noDuplicateEffect = true,
                contentSha256 = observed.ContentSha256,
                contentLength = observed.ContentLength,
                controlSha256 = observed.ControlSha256,
                controlLength = observed.ControlLength,
                outcome = observed.Outcome.Outcome.ToString(),
                receiptId = observed.Outcome.ReceiptId
            }));
        }
        finally { Need(await provider.StopAsync(new(), default)); }
    }

    private static void Save(string path, ArtifactCrashState state)
    {
        var bytes = JsonSerializer.SerializeToUtf8Bytes(state);
        Require(bytes.Length <= 16384, "Artifact crash state exceeded its bound.");
        using var file = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read);
        file.Write(bytes);
        file.Flush(flushToDisk: true);
    }

    private sealed class Registration(LocalFaultControls faults, string point) : IAsyncDisposable
    {
        public ValueTask DisposeAsync()
        {
            faults.RemoveObserver(point);
            return ValueTask.CompletedTask;
        }
    }

    private static T Need<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failure
                ? "Artifact crash operation failed: " + failure.Code : "Artifact crash operation failed.");
    private static void Require(bool condition, string message)
    { if (!condition) { throw new InvalidOperationException(message); } }
}
