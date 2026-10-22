using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.TransferRunner;

if (args.Length != 5 || args[0] is not ("local" or "object")
    || !long.TryParse(args[2], out var size) || size is not (268435456L or 4294967296L)
    || args[3].Length != 64 || args[3].Any(character => !char.IsAsciiHexDigitLower(character)))
{
    Console.Error.WriteLine("Artifact transfer requires a fixture, root, qualified size, expected hash and run ID.");
    return 2;
}

await using var store = await ArtifactFixtureSession.CreateForQualificationAsync(args[0], args[1],
    limits: new ArtifactLimits(transferSlots: 1));
using (var warmSource = new GeneratedSource(8388608))
{
    var warmTicket = Require(await store.Store.ReserveWriteAsync(new(new ArtifactExpectations(8388608)), new(), default));
    var warm = Require(await store.Store.StageAsync(warmTicket, warmSource, new(), default));
    var warmReceipt = Require(await store.Store.CommitAsync(warm, new(), default));
    await using var read = Require(await store.Store.OpenReadAsync(new(warmReceipt.Stamp.Identity.Digest), new(), default));
    using var sink = new HashingSink();
    Require(await read.CopyToAsync(sink, new(), default));
}
GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
Console.WriteLine(JsonSerializer.Serialize(new
{
    eventName = "idle",
    pid = Environment.ProcessId,
    runtime = RuntimeInformation.FrameworkDescription,
    baselineRssBytes = Process.GetCurrentProcess().WorkingSet64
}));
if (await Console.In.ReadLineAsync() != "transfer")
{ Console.Error.WriteLine("Artifact transfer received no owner handshake."); return 2; }

var digest = new ArtifactDigest(args[3]);
using var source = new GeneratedSource(size);
var ticket = Require(await store.Store.ReserveWriteAsync(new(new ArtifactExpectations(size,
    new ArtifactOption<ArtifactDigest>.Some(digest), new ArtifactOption<long>.Some(size))), new(), default));
var staged = Require(await store.Store.StageAsync(ticket, source, new(), default));
var receipt = Require(await store.Store.CommitAsync(staged, new(), default));
using var destination = new HashingSink();
await using (var read = Require(await store.Store.OpenReadAsync(new(digest,
    expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default)))
{
    Require(await read.CopyToAsync(destination, new(), default));
}
var sourceHash = source.Digest;
var sinkHash = destination.Digest;
if (source.BytesRead != size || destination.BytesWritten != size || sourceHash != args[3] || sinkHash != args[3]
    || !source.Paced || !destination.Paced || staged.Identity.Length != size)
{ throw new InvalidOperationException("Artifact transfer did not verify actual paced byte counts."); }
Console.WriteLine(JsonSerializer.Serialize(new
{
    eventName = "complete",
    provider = args[0],
    runId = args[4],
    pid = Environment.ProcessId,
    size,
    written = source.BytesRead,
    read = destination.BytesWritten,
    expectedSha256 = args[3],
    sourceSha256 = sourceHash,
    sinkSha256 = sinkHash,
    runtime = RuntimeInformation.FrameworkDescription,
    sourcePaced = source.Paced,
    sinkPaced = destination.Paced,
    nonSeekable = true,
    generated = true,
    independentExpectedHash = true,
    warmupComplete = true,
    bufferBytes = store.Store.Capabilities.Limits.CopyBufferBytes,
    providerBufferLimit = store.Store.Capabilities.Limits.TransferBufferBytes,
    slots = store.Store.Capabilities.Limits.TransferSlots
}));
return 0;

static T Require<T>(ArtifactResult<T> result) where T : notnull
    => result is ArtifactResult<T>.Success success ? success.Value
        : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failed
            ? $"Artifact transfer failed ({failed.Code})." : "Unknown artifact transfer result.");
