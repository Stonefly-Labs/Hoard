using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Hoard.Conformance.Tests;

internal static class MetadataRecoverySource
{
    internal const string Identity = "Hoard.Conformance.Tests.MetadataRecoveryRuntimeTests."
        + "Complete_current_input_native_recovery_graph_preserves_all_barriers_and_readbacks";

    internal static void Verify(string contextPath)
    {
        using var context = JsonDocument.Parse(ReadFile(contextPath, 1024 * 1024));
        var header = context.RootElement;
        Fields(header, "schemaVersion", "runId", "invocationGroupId", "attemptId", "rootId",
            "inputsSha256", "rootPath", "graphPath", "sourcePath", "outputDirectory", "files");
        Assert.Equal(1, header.GetProperty("schemaVersion").GetInt32());
        foreach (var name in new[] { "runId", "invocationGroupId", "attemptId", "rootId" })
        {
            Assert.True(Guid.TryParse(Text(header, name), out var id));
            Assert.NotEqual(Guid.Empty, id);
        }
        HashValue(Text(header, "inputsSha256"));
        var root = Text(header, "rootPath");
        Assert.True(Path.IsPathFullyQualified(root));
        Assert.Equal(Path.GetFullPath(root), root);
        var expected = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var file in header.GetProperty("files").EnumerateObject())
        {
            Assert.Equal(InsideRoot(file.Name), file.Name);
            var hash = Assert.IsType<string>(file.Value.GetString());
            HashValue(hash);
            Assert.True(expected.TryAdd(file.Name, hash));
        }
        Assert.Equal(65, expected.Count);
        var consumed = new Dictionary<string, string>(StringComparer.Ordinal);
        var totalBytes = 0;
        var started = Stopwatch.GetTimestamp();

        using var graphDocument = ReadJson(Text(header, "graphPath"), 256 * 1024);
        var graph = graphDocument.RootElement;
        Fields(graph, "schemaVersion", "qualification", "runId", "invocationGroupId", "inputsSha256",
            "assemblyPath", "inputsPath", "commands", "sourceReceiptSha256");
        Assert.Equal(1, graph.GetProperty("schemaVersion").GetInt32());
        Assert.False(graph.GetProperty("qualification").GetBoolean());
        foreach (var name in new[] { "runId", "invocationGroupId", "inputsSha256" })
        { Assert.Equal(Text(header, name), Text(graph, name)); }
        var inputsPath = Text(graph, "inputsPath");
        using var inputsDocument = ReadJson(inputsPath, 16 * 1024 * 1024);
        var inputs = inputsDocument.RootElement;
        Assert.Equal(Text(header, "inputsSha256"), consumed[InsideRoot(inputsPath)]);
        Assert.Equal("metadata", Text(inputs, "profileId"));
        foreach (var name in new[] { "runId", "invocationGroupId" })
        { Assert.Equal(Text(header, name), Text(inputs, name)); }
        var mode = Text(inputs, "mode");
        Assert.Contains(mode, new[] { "diagnostic", "qualification" });
        var prefix = mode == "qualification" ? "qualification-sqlite-recovery" : "category-sqlite-recovery";
        Assert.Equal($"proofs/{prefix}-native-inputs.json", inputsPath);
        Assert.Equal($"proofs/{prefix}-native-executions.json", Text(header, "graphPath"));
        Assert.Equal($"proofs/{prefix}.json", Text(header, "sourcePath"));
        var assembly = Text(graph, "assemblyPath");
        InsideRoot(assembly);
        var assemblyHash = Text(inputs.GetProperty("runtimeAssemblies"), assembly);
        HashValue(assemblyHash);
        using var sourceDocument = ReadJson(Text(header, "sourcePath"), 64 * 1024);
        Assert.Equal(Text(graph, "sourceReceiptSha256"), consumed[InsideRoot(Text(header, "sourcePath"))]);
        var source = sourceDocument.RootElement;
        Fields(source, "qualification", "mode", "code", "inputsSha256", "barriers", "walkthroughSha256");
        Assert.False(source.GetProperty("qualification").GetBoolean());
        Assert.Equal("metadata-recovery", Text(source, "mode"));
        Assert.Equal("None", Text(source, "code"));
        Assert.Equal(Text(header, "inputsSha256"), Text(source, "inputsSha256"));
        var commands = graph.GetProperty("commands").EnumerateArray().ToArray();
        var barriers = source.GetProperty("barriers").EnumerateArray().ToArray();
        Assert.Equal(31, commands.Length);
        Assert.Equal(10, barriers.Length);
        var rowIndex = 0;
        var barrierIndex = 0;
        var previousSequence = 0;
        var previousEnd = 0d;
        foreach (var (kind, names, offset) in new[]
        {
            ("mutation", new[] { "M0", "M1", "M2" }, 0),
            ("upgrade", new[] { "U0", "U1", "U2", "U3", "U4" }, 10),
            ("restore", new[] { "R0", "R1" }, 20)
        })
        {
            for (var index = 0; index < names.Length; index++)
            {
                var hashes = new List<string>();
                string? childStart = null;
                foreach (var step in new[] { "seed", "run", "recover" })
                {
                    var result = VerifyCommand(commands[rowIndex++], step + "-" + kind, names[index],
                        step == "run" ? offset + index : null);
                    hashes.Add(result.Hash);
                    if (step == "run") { childStart = result.ChildStart; }
                }
                var barrier = barriers[barrierIndex++];
                Fields(barrier, "barrierId", "value", "seedSha256", "controllerSha256", "readbackSha256", "childStartSha256");
                Assert.Equal(names[index], Text(barrier, "barrierId"));
                Assert.Equal(offset + index, barrier.GetProperty("value").GetInt32());
                Assert.Equal(hashes[0], Text(barrier, "seedSha256"));
                Assert.Equal(hashes[1], Text(barrier, "controllerSha256"));
                Assert.Equal(hashes[2], Text(barrier, "readbackSha256"));
                Assert.Equal(childStart, Text(barrier, "childStartSha256"));
            }
        }
        Assert.Equal(VerifyCommand(commands[rowIndex], "recovery-walkthrough", "none", null).Hash,
            Text(source, "walkthroughSha256"));
        Assert.Equal(expected.Count, consumed.Count);
        Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
        var output = InsideRoot(Text(header, "outputDirectory"));
        Assert.True(Directory.Exists(output));
        Assert.Equal(FileAttributes.Directory,
            File.GetAttributes(output) & (FileAttributes.Directory | FileAttributes.ReparsePoint));
        var packet = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            qualification = false,
            runId = Text(header, "runId"),
            attemptId = Text(header, "attemptId"),
            inputsSha256 = Text(header, "inputsSha256"),
            testIdentity = Identity,
            files = consumed.ToDictionary(file => Hash(Encoding.UTF8.GetBytes(file.Key)), file => file.Value)
        });
        using var destination = new FileStream(Path.Combine(output,
            "metadata-recovery-" + Hash(Encoding.UTF8.GetBytes(Identity)) + ".json"), FileMode.CreateNew, FileAccess.Write);
        destination.Write(packet);

        string InsideRoot(string path)
        {
            var absolute = Path.GetFullPath(Path.Combine(root, path));
            Assert.StartsWith(root + Path.DirectorySeparatorChar, absolute, StringComparison.Ordinal);
            return absolute;
        }

        JsonDocument ReadJson(string relative, int limit)
        {
            Assert.False(Path.IsPathFullyQualified(relative));
            var path = InsideRoot(relative);
            Assert.True(expected.TryGetValue(path, out var hash));
            var bytes = ReadFile(path, Math.Min(limit, 16 * 1024 * 1024 - totalBytes));
            Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
            totalBytes += bytes.Length;
            Assert.Equal(hash, Hash(bytes));
            Assert.True(consumed.TryAdd(path, Hash(bytes)));
            return JsonDocument.Parse(bytes);
        }

        (string Hash, string ChildStart) VerifyCommand(JsonElement row, string commandMode, string barrierId, int? barrier)
        {
            Fields(row, "mode", "barrierId", "sequence", "controllerSha256", "executionSha256");
            Assert.Equal(commandMode, Text(row, "mode"));
            Assert.Equal(barrierId, Text(row, "barrierId"));
            var sequence = row.GetProperty("sequence").GetInt32();
            Assert.True(sequence > previousSequence);
            using var controlDocument = ReadJson($"proofs/recovery-command-{sequence:D4}.json", 64 * 1024);
            using var nativeDocument = ReadJson($"proofs/execution-command-{sequence:D4}.json", 64 * 1024);
            var control = controlDocument.RootElement;
            var native = nativeDocument.RootElement;
            var common = new[] { "schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs",
                "endedMs", "exitCode", "diagnosticCode", "groupState", "scope" };
            Fields(control, barrier is null ? common : [.. common, "barrier"]);
            Fields(native, [.. common, "runId", "rootId", "argvSha256", "cwdSha256", "controlRecordSha256", "inputFiles"]);
            foreach (var name in common)
            { Assert.Equal(control.GetProperty(name).GetRawText(), native.GetProperty(name).GetRawText()); }
            Assert.Equal(1, control.GetProperty("schemaVersion").GetInt32());
            Assert.Equal(sequence, control.GetProperty("sequence").GetInt32());
            Assert.InRange(control.GetProperty("childPid").GetInt32(), 2, int.MaxValue);
            HashValue(Text(control, "childStartSha256"));
            Assert.NotEqual(new string('0', 64), Text(control, "childStartSha256"));
            Assert.Equal(barrier is null ? 0 : -9, control.GetProperty("exitCode").GetInt32());
            Assert.Equal("None", Text(control, "diagnosticCode"));
            Assert.Equal("Exited", Text(control, "groupState"));
            Assert.Equal("recovery", Text(control, "scope"));
            var start = control.GetProperty("startedMs").GetDouble();
            var end = control.GetProperty("endedMs").GetDouble();
            Assert.InRange(start, previousEnd, long.MaxValue);
            Assert.InRange(end, start, start + (barrier is null ? 300000 : 15000));
            if (barrier is not null)
            {
                var observed = control.GetProperty("barrier");
                Fields(observed, "value", "observedMs", "signalMs");
                Assert.Equal(barrier.Value, observed.GetProperty("value").GetInt32());
                var seen = observed.GetProperty("observedMs").GetDouble();
                Assert.InRange(seen, start, end);
                Assert.InRange(observed.GetProperty("signalMs").GetDouble(), seen, end);
            }
            foreach (var name in new[] { "runId", "rootId" })
            { Assert.Equal(Text(header, name), Text(native, name)); }
            HashValue(Text(native, "argvSha256"));
            HashValue(Text(native, "cwdSha256"));
            var inputFiles = native.GetProperty("inputFiles");
            Fields(inputFiles, assembly, inputsPath);
            Assert.Equal(assemblyHash, Text(inputFiles, assembly));
            Assert.Equal(Text(header, "inputsSha256"), Text(inputFiles, inputsPath));
            var controlHash = consumed[InsideRoot($"proofs/recovery-command-{sequence:D4}.json")];
            Assert.Equal(controlHash, Text(row, "controllerSha256"));
            Assert.Equal(controlHash, Text(native, "controlRecordSha256"));
            Assert.Equal(consumed[InsideRoot($"proofs/execution-command-{sequence:D4}.json")],
                Text(row, "executionSha256"));
            previousSequence = sequence;
            previousEnd = end;
            return (controlHash, Text(control, "childStartSha256"));
        }
    }

    internal static string Text(JsonElement value, string name)
        => Assert.IsType<string>(value.GetProperty(name).GetString());

    internal static void Fields(JsonElement value, params string[] names)
        => Assert.Equal(names.Order(), value.EnumerateObject().Select(item => item.Name).Order());

    internal static void HashValue(string value)
        => Assert.Matches("^[0-9a-f]{64}$", value);

    internal static string Hash(byte[] value) => Convert.ToHexStringLower(SHA256.HashData(value));

    internal static byte[] ReadFile(string path, int limit)
    {
        Assert.InRange(limit, 0, 16 * 1024 * 1024);
        Assert.Equal(0, (int)(File.GetAttributes(path) & (FileAttributes.Directory | FileAttributes.ReparsePoint)));
        var started = Stopwatch.GetTimestamp();
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Assert.InRange(stream.Length, 1, limit);
        var bytes = new byte[checked((int)stream.Length)];
        var offset = 0;
        while (offset < bytes.Length)
        {
            Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
            var count = stream.Read(bytes, offset, Math.Min(65536, bytes.Length - offset));
            Assert.True(count > 0);
            offset += count;
        }
        Assert.Equal(-1, stream.ReadByte());
        Assert.Equal(bytes.Length, stream.Length);
        Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
        return bytes;
    }
}
