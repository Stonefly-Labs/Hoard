using System.Text.Json.Nodes;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactTransferProofTests
{
    [Theory]
    [InlineData("local", 268435456L)]
    [InlineData("local", 4294967296L)]
    [InlineData("object", 268435456L)]
    [InlineData("object", 4294967296L)]
    public void Measured_transfer_binds_actual_bytes_pacing_hashes_and_os_peak(string provider, long size)
    {
        var root = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_TRANSFER_PROOFS")
            ?? throw new InvalidOperationException("Actual measured transfer proofs are required.");
        var run = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_RUN_ID")
            ?? throw new InvalidOperationException("Current artifact run attribution is required.");
        var path = Path.Combine(root, $"transfer-{provider}-{size}", "proof.json");
        Assert.InRange(new FileInfo(path).Length, 1, 16384);
        var sourceBytes = File.ReadAllBytes(path);
        var proof = Assert.IsType<JsonObject>(JsonNode.Parse(sourceBytes));
        Verify(proof);
        foreach (var (field, value) in new (string, JsonNode?)[]
        {
            ("provider", JsonValue.Create(provider == "local" ? "object" : "local")),
            ("runId", JsonValue.Create("foreign-run")), ("written", JsonValue.Create(size - 1)),
            ("read", JsonValue.Create(size - 1)), ("sourceSha256", JsonValue.Create(new string('0', 64))),
            ("sinkSha256", JsonValue.Create(new string('0', 64))), ("sourcePaced", JsonValue.Create(false)),
            ("sinkPaced", JsonValue.Create(false)), ("generated", JsonValue.Create(false)),
            ("warmupComplete", JsonValue.Create(false)), ("nonSeekable", JsonValue.Create(false)),
            ("independentExpectedHash", JsonValue.Create(false)), ("baselineRssBytes", JsonValue.Create(0L)),
            ("osPeakRssBytes", JsonValue.Create(proof["baselineRssBytes"]!.GetValue<long>() + 67108865)),
            ("bufferBytes", JsonValue.Create(4194304)), ("slots", JsonValue.Create(4)),
            ("samples", JsonValue.Create(0)), ("exitCode", JsonValue.Create(1)),
            ("osPeakMethod", JsonValue.Create("declared"))
        })
        {
            var changed = Assert.IsType<JsonObject>(proof.DeepClone());
            changed[field] = value;
            Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => Verify(changed));
        }
        ArtifactSourceCapture.PublishIfRequested(FormattableString.Invariant(
            $"{typeof(ArtifactTransferProofTests).FullName}.{nameof(Measured_transfer_binds_actual_bytes_pacing_hashes_and_os_peak)}(provider: \"{provider}\", size: {size})"),
            (path, sourceBytes));

        void Verify(JsonObject value)
        {
            Assert.Equal(provider, value["provider"]!.GetValue<string>());
            Assert.Equal(run, value["runId"]!.GetValue<string>());
            Assert.Equal(size, value["size"]!.GetValue<long>());
            Assert.Equal(size, value["written"]!.GetValue<long>());
            Assert.Equal(size, value["read"]!.GetValue<long>());
            var expected = size == 268435456
                ? "113c39a8d2254b64b3df2bdfeeaeb80c277bf4f68ea42510e7cf97e4b8467fb2"
                : "f3492797d78d20782483a505e9a249466dc027f86615e647f4719cd7e93301b2";
            foreach (var field in new[] { "expectedSha256", "sourceSha256", "sinkSha256" })
            { Assert.Equal(expected, value[field]!.GetValue<string>()); }
            foreach (var field in new[] { "sourcePaced", "sinkPaced", "nonSeekable", "generated", "independentExpectedHash", "warmupComplete" })
            { Assert.True(value[field]!.GetValue<bool>()); }
            var baseline = value["baselineRssBytes"]!.GetValue<long>();
            var peak = value["osPeakRssBytes"]!.GetValue<long>();
            Assert.True(baseline > 0);
            Assert.InRange(peak - baseline, 0, 67108864);
            Assert.InRange(value["sampledPeakRssBytes"]!.GetValue<long>(), baseline, peak);
            Assert.True(value["samples"]!.GetValue<int>() >= 2);
            Assert.True(value["pid"]!.GetValue<int>() > 0);
            Assert.Equal(0, value["exitCode"]!.GetValue<int>());
            Assert.Equal("bytes", value["rssUnits"]!.GetValue<string>());
            Assert.Contains(value["osPeakMethod"]!.GetValue<string>(), new[] { "time-l", "time-v", "getrusage", "proc-status" });
            Assert.False(string.IsNullOrWhiteSpace(value["runtime"]!.GetValue<string>()));
            Assert.Equal(262144, value["bufferBytes"]!.GetValue<int>());
            Assert.Equal(2097152, value["providerBufferLimit"]!.GetValue<int>());
            Assert.Equal(1, value["slots"]!.GetValue<int>());
        }
    }
}
