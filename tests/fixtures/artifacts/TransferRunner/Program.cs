using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;

if (args.Length is not (5 or 6) || args[0] is not ("local" or "object")
    || !long.TryParse(args[2], out var size) || size is not (268435456L or 4294967296L)
    || args[3].Length != 64 || args[3].Any(character => !char.IsAsciiHexDigitLower(character)))
{
    Console.Error.WriteLine("Artifact transfer requires a fixture, root, qualified size, expected hash and run ID.");
    return 2;
}

var safeEvents = Environment.GetEnvironmentVariable("HOARD_CONFORMANCE_SAFE_EVENTS") switch
{
    null => false,
    "1" => true,
    _ => throw new ArgumentException("Unsupported artifact transfer event mode.")
};
if (safeEvents && !Guid.TryParseExact(args[4], "D", out _))
{ throw new ArgumentException("Safe artifact transfer requires an exact run ID."); }
if (args.Length == 6 && (!safeEvents || !Path.IsPathFullyQualified(args[5]) || Path.GetFullPath(args[5]) != args[5]))
{ throw new ArgumentException("Sealed artifact transfer proof requires safe events and an exact absolute output path."); }

await using var store = await ArtifactFixtureSession.CreateForQualificationAsync(args[0], args[1],
    limits: new ArtifactLimits(transferSlots: 1));
await ArtifactTransferAssertions.WarmAsync(store.Store);
GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
Console.WriteLine(safeEvents ? "{\"event\":\"control\",\"code\":\"None\",\"value\":0}" : JsonSerializer.Serialize(new
{
    eventName = "idle",
    pid = Environment.ProcessId,
    runtime = RuntimeInformation.FrameworkDescription,
    baselineRssBytes = Process.GetCurrentProcess().WorkingSet64
}));
Console.Out.Flush();
if (await Console.In.ReadLineAsync() != "transfer")
{ Console.Error.WriteLine("Artifact transfer received no owner handshake."); return 2; }

var transfer = await ArtifactTransferAssertions.TransferAsync(store.Store, size, args[3]);
var completion = JsonSerializer.Serialize(new
{
    eventName = "complete",
    provider = args[0],
    runId = args[4],
    pid = Environment.ProcessId,
    size,
    written = transfer.Written,
    read = transfer.Read,
    expectedSha256 = args[3],
    sourceSha256 = transfer.SourceSha256,
    sinkSha256 = transfer.SinkSha256,
    runtime = RuntimeInformation.FrameworkDescription,
    sourcePaced = transfer.SourcePaced,
    sinkPaced = transfer.SinkPaced,
    nonSeekable = true,
    generated = true,
    independentExpectedHash = true,
    warmupComplete = true,
    bufferBytes = store.Store.Capabilities.Limits.CopyBufferBytes,
    providerBufferLimit = store.Store.Capabilities.Limits.TransferBufferBytes,
    slots = store.Store.Capabilities.Limits.TransferSlots
});
if (safeEvents)
{
    var proof = System.Text.Encoding.UTF8.GetBytes(completion);
    if (proof.Length > 8192)
    { throw new InvalidOperationException("Artifact transfer proof exceeded its bound."); }
    await using (var output = new FileStream(Path.Combine(args[1], "transfer-proof.json"),
        FileMode.CreateNew, FileAccess.Write, FileShare.None))
    {
        await output.WriteAsync(proof);
        output.Flush(flushToDisk: true);
    }
    if (args.Length == 6)
    {
        await using var output = new FileStream(args[5], FileMode.CreateNew, FileAccess.Write, FileShare.None);
        await output.WriteAsync(proof);
        output.Flush(flushToDisk: true);
    }
    Console.WriteLine(JsonSerializer.Serialize(new { @event = "test", code = "None", value = size }));
    Console.Out.Flush();
    if (await Console.In.ReadLineAsync() != "settle")
    { throw new InvalidOperationException("Artifact transfer received no owner settlement."); }
    Console.WriteLine("{\"event\":\"control\",\"code\":\"None\",\"value\":1}");
    Console.Out.Flush();
}
else
{ Console.WriteLine(completion); }
return 0;
