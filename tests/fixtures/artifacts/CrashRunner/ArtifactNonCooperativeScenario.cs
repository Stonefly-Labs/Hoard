using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;

internal static class ArtifactNonCooperativeScenario
{
    public static async Task<int> ExecuteAsync(string[] args)
    {
        var safeEvents = Environment.GetEnvironmentVariable("HOARD_CONFORMANCE_SAFE_EVENTS") switch
        {
            null => false,
            "1" => true,
            _ => throw new ArgumentException("Unsupported artifact non-cooperative event mode.")
        };
        var root = Path.GetFullPath(args[1]);
        var provider = args[2];
        var scenario = args[3];
        var run = Guid.Parse(args[4]);
        if (provider is not ("local" or "object") || scenario is not ("source" or "destination" or "native"))
        { throw new ArgumentException("Unknown non-cooperative artifact scenario."); }
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var localFaults = new LocalFaultControls();
        var objectFaults = new ObjectFaultControls();
        IArtifactStoreLifetime lifetime = provider == "local"
            ? new LocalArtifactStore(root, controls: localFaults) : new ObjectArtifactStore(root, controls: objectFaults);
        Need(await lifetime.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority,
            new ArtifactLimits(transferSlots: 1, waitingCalls: 0)), new(), default));
        var store = (IArtifactStore)lifetime;
        using var parent = new CancellationTokenSource(TimeSpan.FromMinutes(4));
        await ArtifactNonCooperationAssertions.ExecuteAsync(store, lifetime, authority, identity, scenario,
            token =>
            {
                token.ThrowIfCancellationRequested();
                var hold = new NativeHold(() =>
                {
                    if (provider == "local") { localFaults.BeforeRecordWrite = null; }
                    else { objectFaults.BeforeObjectDelete = null; }
                });
                if (provider == "local") { localFaults.BeforeRecordWrite = hold.Block; }
                else { objectFaults.BeforeObjectDelete = hold.Block; }
                return ValueTask.FromResult<IArtifactSynchronousHold>(hold);
            },
            () => lifetime switch
            {
                LocalArtifactStore local => local.WhenIdleForQualificationAsync(),
                ObjectArtifactStore objects => objects.WhenIdleForQualificationAsync(),
                _ => throw new InvalidOperationException("Unknown artifact child store.")
            },
            () => new(Directory.Exists(root), lifetime switch
            {
                LocalArtifactStore local => local.Ready,
                ObjectArtifactStore objects => objects.Ready,
                _ => throw new InvalidOperationException("Unknown artifact child store.")
            }),
            async (mode, token) =>
            {
                IArtifactStoreLifetime competing = provider == "local" ? new LocalArtifactStore(root) : new ObjectArtifactStore(root);
                ArtifactResult<ArtifactAdmission> admission;
                ArtifactResult<ArtifactShutdown> shutdown;
                try { admission = await competing.InitializeAsync(new(mode, identity, authority), new(), token); }
                finally { shutdown = await competing.StopAsync(new(), default); }
                return new(admission, shutdown);
            }, InspectAsync, parent.Token);
        return 1;

        async ValueTask InspectAsync(string phase, ArtifactNonCooperationReadback readback)
        {
            var observation = JsonSerializer.Serialize(new
            {
                eventName = "noncooperative",
                phase,
                pid = Environment.ProcessId,
                runId = run,
                provider,
                scenario,
                durableCrashProof = false,
                cleanup = readback.Cleanup.ToString(),
                callerCode = readback.CallerCode.ToString(),
                admissionCode = readback.AdmissionCode.ToString(),
                shutdownCode = readback.ShutdownCode.ToString(),
                enteredWorkers = readback.EnteredWorkers,
                workerPending = readback.WorkerPending,
                borrowedStreamsIntact = readback.BorrowedStreamsIntact,
                rootStillOwned = readback.RootStillOwned,
                readinessBlocked = readback.ReadinessBlocked,
                protectionRetained = readback.ProtectionRetained
            });
            if (safeEvents)
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(observation);
                if (bytes.Length > 8192)
                { throw new InvalidOperationException("Artifact non-cooperative proof exceeded its bound."); }
                using (var output = new FileStream(Path.Combine(root, $"noncooperative-{phase}.json"),
                    FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    output.Write(bytes);
                    output.Flush(flushToDisk: true);
                }
                var offset = scenario switch { "source" => 0, "destination" => 1, "native" => 2, _ => throw new InvalidOperationException() };
                var value = (phase == "contained" ? 60 : 70) + offset;
                Console.WriteLine(JsonSerializer.Serialize(new { @event = "barrier", code = "None", value }));
            }
            else
            { Console.WriteLine(observation); }
            await Console.Out.FlushAsync();
            if (phase == "contained")
            { Require(await Console.In.ReadLineAsync(parent.Token) == "inspect"); }
        }
    }

    private static T Need<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException("Artifact child control operation failed.");

    private static void Require(bool condition)
    {
        if (!condition) { throw new InvalidOperationException("Artifact non-cooperative containment assertion failed."); }
    }

    private sealed class NativeHold(Action clear) : IArtifactSynchronousHold
    {
        private int count;
        private readonly ManualResetEventSlim native = new();
        private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public long ObservationCount => Volatile.Read(ref count);
        public ValueTask WaitForEntryAsync(CancellationToken cancellationToken) =>
            new(entered.Task.WaitAsync(TimeSpan.FromSeconds(10), cancellationToken));
        public void Block() { Interlocked.Increment(ref count); entered.TrySetResult(); native.Wait(); }
        public void Release() => native.Set();
        public ValueTask DisposeAsync() { Release(); clear(); return ValueTask.CompletedTask; }
    }
}
