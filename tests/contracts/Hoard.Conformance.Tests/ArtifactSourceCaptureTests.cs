using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Artifacts.Tests;

namespace Hoard.Conformance.Tests;

public sealed class ArtifactSourceCaptureTests
{
    private const string Identity = "Hoard.Artifacts.Tests.ArtifactTransferProofTests."
        + "Measured_transfer_binds_actual_bytes_pacing_hashes_and_os_peak(provider: \"local\", size: 268435456)";

    [Fact]
    public void Capture_binds_actual_consumed_bytes_and_creates_one_hash_only_packet()
    {
        using var owned = new OwnedCapture();
        ArtifactSourceCapture.Publish(owned.ContextPath, Identity, (owned.ProofPath, owned.Bytes));
        var path = Assert.Single(Directory.GetFiles(owned.Output));
        var bytes = File.ReadAllBytes(path);
        using var document = JsonDocument.Parse(bytes);
        var packet = document.RootElement;
        Assert.Equal(1, packet.GetProperty("schemaVersion").GetInt32());
        Assert.False(packet.GetProperty("qualification").GetBoolean());
        Assert.Equal(owned.RunId, packet.GetProperty("runId").GetGuid());
        Assert.Equal(Identity, packet.GetProperty("testIdentity").GetString());
        Assert.Equal(new string('a', 64), packet.GetProperty("inputsSha256").GetString());
        var file = Assert.Single(packet.GetProperty("files").EnumerateObject());
        Assert.Equal(Hash(Encoding.UTF8.GetBytes(owned.ProofPath)), file.Name);
        Assert.Equal(Hash(owned.Bytes), file.Value.GetString());
        Assert.Equal("artifact-source-" + Hash(Encoding.UTF8.GetBytes(Identity)) + ".json", Path.GetFileName(path));
        Assert.DoesNotContain(owned.Root, Encoding.UTF8.GetString(bytes), StringComparison.Ordinal);
        Assert.DoesNotContain("synthetic-proof-canary", Encoding.UTF8.GetString(bytes), StringComparison.Ordinal);
        Assert.Throws<IOException>(() => ArtifactSourceCapture.Publish(
            owned.ContextPath, Identity, (owned.ProofPath, owned.Bytes)));
        Assert.Equal(bytes, File.ReadAllBytes(path));
    }

    [Theory]
    [InlineData("changed-bytes")]
    [InlineData("missing-file")]
    [InlineData("unknown-field")]
    [InlineData("duplicate-field")]
    [InlineData("duplicate-source")]
    [InlineData("outside-source")]
    [InlineData("oversized-source")]
    public void Invalid_capture_cannot_emit_a_success_packet(string defect)
    {
        using var owned = new OwnedCapture();
        var bytes = owned.Bytes;
        var path = owned.ProofPath;
        if (defect == "changed-bytes") { File.WriteAllText(path, "changed"); }
        else if (defect == "missing-file") { File.Delete(path); }
        else if (defect == "unknown-field") { owned.WriteContext(extra: true); }
        else if (defect == "duplicate-field")
        {
            File.WriteAllText(owned.ContextPath, File.ReadAllText(owned.ContextPath)
                .Replace("\"schemaVersion\":1", "\"schemaVersion\":1,\"schemaVersion\":1", StringComparison.Ordinal));
        }
        else if (defect == "duplicate-source") { owned.WriteContext(duplicate: true); }
        else if (defect == "outside-source")
        {
            path = owned.ContextPath;
            bytes = File.ReadAllBytes(path);
            owned.WriteContext(source: Path.Combine(owned.Root, "..", "foreign.json"));
        }
        else { bytes = new byte[16385]; File.WriteAllBytes(path, bytes); }
        if (defect == "missing-file")
        {
            Assert.ThrowsAny<IOException>(() => ArtifactSourceCapture.Publish(
                owned.ContextPath, Identity, (path, bytes)));
        }
        else
        {
            Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => ArtifactSourceCapture.Publish(
                owned.ContextPath, Identity, (path, bytes)));
        }
        Assert.Empty(Directory.GetFiles(owned.Output));
    }

    [Fact]
    public void Context_copied_outside_its_declared_root_cannot_publish()
    {
        using var owned = new OwnedCapture();
        using var foreign = new OwnedCapture();
        File.WriteAllBytes(foreign.ContextPath, File.ReadAllBytes(owned.ContextPath));
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => ArtifactSourceCapture.Publish(
            foreign.ContextPath, Identity, (owned.ProofPath, owned.Bytes)));
        Assert.Empty(Directory.GetFiles(owned.Output));
        Assert.Empty(Directory.GetFiles(foreign.Output));
    }

    [Fact]
    public void Symbolic_source_link_cannot_substitute_identical_bytes()
    {
        using var owned = new OwnedCapture();
        var actual = Path.Combine(owned.Root, "actual.json");
        File.Move(owned.ProofPath, actual);
        File.CreateSymbolicLink(owned.ProofPath, actual);
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => ArtifactSourceCapture.Publish(
            owned.ContextPath, Identity, (owned.ProofPath, owned.Bytes)));
        Assert.Empty(Directory.GetFiles(owned.Output));
    }

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private sealed class OwnedCapture : IDisposable
    {
        internal string Root { get; } = Path.GetFullPath(Path.Combine(
            ".artifact-source-capture-tests", Guid.NewGuid().ToString("D")));
        internal Guid RunId { get; } = Guid.NewGuid();
        internal string ContextPath => Path.Combine(Root, "context.json");
        internal string ProofPath => Path.Combine(Root, "proof.json");
        internal string Output => Path.Combine(Root, "capture");
        internal byte[] Bytes { get; } = Encoding.UTF8.GetBytes("synthetic-proof-canary");

        internal OwnedCapture()
        {
            Directory.CreateDirectory(Output);
            File.WriteAllBytes(ProofPath, Bytes);
            WriteContext();
        }

        internal void WriteContext(bool extra = false, bool duplicate = false, string? source = null)
        {
            var context = new Dictionary<string, object>
            {
                ["schemaVersion"] = 1,
                ["runId"] = RunId,
                ["invocationGroupId"] = Guid.NewGuid(),
                ["attemptId"] = Guid.NewGuid(),
                ["rootId"] = Guid.NewGuid().ToString("N"),
                ["inputsSha256"] = new string('a', 64),
                ["rootPath"] = Root,
                ["outputDirectory"] = Output,
                ["cases"] = new Dictionary<string, string[]>
                {
                    [Identity] = duplicate ? [ProofPath, ProofPath] : [source ?? ProofPath]
                }
            };
            if (extra) { context["unexpected"] = "synthetic-proof-canary"; }
            File.WriteAllBytes(ContextPath, JsonSerializer.SerializeToUtf8Bytes(context));
        }

        public void Dispose() => Directory.Delete(Root, recursive: true);
    }
}
