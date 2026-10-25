using System.Diagnostics;
using System.Text;
using System.Text.Json;
using static Hoard.Conformance.Tests.MetadataRecoverySource;

namespace Hoard.Conformance.Tests;

internal static class MetadataInventorySource
{
    internal static void Verify(string contextPath, string identity)
    {
        using var contextDocument = JsonDocument.Parse(ReadFile(contextPath, 1024 * 1024));
        var context = contextDocument.RootElement;
        Fields(context, "schemaVersion", "runId", "invocationGroupId", "attemptId", "rootId",
            "inputsSha256", "rootPath", "graphPath", "outputDirectory", "files");
        Assert.Equal(1, context.GetProperty("schemaVersion").GetInt32());
        foreach (var key in new[] { "runId", "invocationGroupId", "attemptId", "rootId" })
        {
            Assert.True(Guid.TryParse(Text(context, key), out var id));
            Assert.NotEqual(Guid.Empty, id);
        }
        HashValue(Text(context, "inputsSha256"));
        var root = Text(context, "rootPath");
        Assert.True(Path.IsPathFullyQualified(root));
        Assert.Equal(Path.GetFullPath(root), root);
        var expected = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var file in context.GetProperty("files").EnumerateObject())
        {
            Assert.Equal(InsideRoot(file.Name), file.Name);
            var hash = Assert.IsType<string>(file.Value.GetString());
            HashValue(hash);
            Assert.True(expected.TryAdd(file.Name, hash));
        }
        Assert.Equal(14, expected.Count);
        var consumed = new Dictionary<string, string>(StringComparer.Ordinal);
        var totalBytes = 0;
        var started = Stopwatch.GetTimestamp();
        const string prefix = "proofs/qualification-metadata-inventory";
        Assert.Equal(prefix + "-native-executions.json", Text(context, "graphPath"));
        using var graphDocument = ReadJson(Text(context, "graphPath"));
        var graph = graphDocument.RootElement;
        Fields(graph, "schemaVersion", "qualification", "runId", "invocationGroupId", "inputsSha256",
            "scriptPath", "inputsPath", "commands");
        Assert.Equal(1, graph.GetProperty("schemaVersion").GetInt32());
        Assert.False(graph.GetProperty("qualification").GetBoolean());
        foreach (var key in new[] { "runId", "invocationGroupId", "inputsSha256" })
        { Assert.Equal(Text(context, key), Text(graph, key)); }
        Assert.Equal("snapshot/scripts/conformance_unit_checks.py", Text(graph, "scriptPath"));
        var inputsPath = prefix + "-native-inputs.json";
        Assert.Equal(inputsPath, Text(graph, "inputsPath"));
        using var inputsDocument = ReadJson(inputsPath);
        var inputs = inputsDocument.RootElement;
        Assert.Equal(Text(context, "inputsSha256"), consumed[InsideRoot(inputsPath)]);
        Assert.Equal("metadata", Text(inputs, "profileId"));
        Assert.Equal("qualification", Text(inputs, "mode"));
        foreach (var key in new[] { "runId", "invocationGroupId" })
        { Assert.Equal(Text(context, key), Text(inputs, key)); }
        var commands = graph.GetProperty("commands").EnumerateArray().ToArray();
        Assert.Equal(3, commands.Length);
        byte[]? original = null;
        string? suiteHash = null, testsHash = null;
        int? testsCount = null;
        var previousSequence = 0;
        var previousEnd = 0d;
        var index = 0;
        foreach (var mode in new[] { "baseline", "mutation", "repair" })
        {
            var row = commands[index++];
            Fields(row, "mode", "sequence", "controllerSha256", "executionSha256");
            Assert.Equal(mode, Text(row, "mode"));
            var sequence = row.GetProperty("sequence").GetInt32();
            Assert.True(sequence > previousSequence);
            var controlPath = $"proofs/recovery-command-{sequence:D4}.json";
            var nativePath = $"proofs/execution-command-{sequence:D4}.json";
            using var controlDocument = ReadJson(controlPath);
            using var nativeDocument = ReadJson(nativePath);
            using var packetDocument = ReadJson(prefix + "-" + mode + ".json");
            var source = Read(prefix + "-" + mode + ".py", 1024 * 1024);
            var control = controlDocument.RootElement;
            var native = nativeDocument.RootElement;
            var packet = packetDocument.RootElement;
            var common = new[] { "schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs",
                "endedMs", "exitCode", "diagnosticCode", "groupState", "scope" };
            Fields(control, common);
            Fields(native, [.. common, "runId", "rootId", "argvSha256", "cwdSha256",
                "controlRecordSha256", "inputFiles", "outputFiles"]);
            foreach (var key in common)
            { Assert.Equal(control.GetProperty(key).GetRawText(), native.GetProperty(key).GetRawText()); }
            Assert.Equal(1, control.GetProperty("schemaVersion").GetInt32());
            Assert.Equal(sequence, control.GetProperty("sequence").GetInt32());
            Assert.InRange(control.GetProperty("childPid").GetInt32(), 2, int.MaxValue);
            HashValue(Text(control, "childStartSha256"));
            Assert.NotEqual(new string('0', 64), Text(control, "childStartSha256"));
            Assert.Equal(mode == "mutation" ? 1 : 0, control.GetProperty("exitCode").GetInt32());
            Assert.Equal("None", Text(control, "diagnosticCode"));
            Assert.Equal("Exited", Text(control, "groupState"));
            Assert.Equal("recovery", Text(control, "scope"));
            var begin = control.GetProperty("startedMs").GetDouble();
            var end = control.GetProperty("endedMs").GetDouble();
            Assert.InRange(begin, previousEnd, long.MaxValue);
            Assert.InRange(end, begin, begin + 300000);
            foreach (var key in new[] { "runId", "rootId" })
            { Assert.Equal(Text(context, key), Text(native, key)); }
            HashValue(Text(native, "argvSha256"));
            HashValue(Text(native, "cwdSha256"));
            Assert.Equal(consumed[InsideRoot(controlPath)], Text(row, "controllerSha256"));
            Assert.Equal(Text(row, "controllerSha256"), Text(native, "controlRecordSha256"));
            Assert.Equal(consumed[InsideRoot(nativePath)], Text(row, "executionSha256"));
            var inputFiles = native.GetProperty("inputFiles");
            var names = new[] { "scripts/conformance_unit_checks.py", "scripts/conformance_sources.py",
                "scripts/conformance_case_catalog.py", "scripts/conformance_evidence.py",
                "scripts/conformance_execution.py", "scripts/conformance_lock_preparation.py",
                "scripts/metadata_evidence.py", "scripts/foundation_evidence.py", "scripts/lifecycle_evidence.py",
                "tests/tooling/test_metadata_evidence.py" };
            Fields(inputFiles, [.. names.Select(name => "snapshot/" + name), inputsPath]);
            foreach (var name in names)
            { Assert.Equal(Text(inputs.GetProperty("sourceManifest"), name), Text(inputFiles, "snapshot/" + name)); }
            Assert.Equal(Text(context, "inputsSha256"), Text(inputFiles, inputsPath));
            var outputs = native.GetProperty("outputFiles");
            Fields(outputs, prefix + "-" + mode + ".json", prefix + "-" + mode + ".py");
            foreach (var file in outputs.EnumerateObject())
            { Assert.Equal(consumed[InsideRoot(file.Name)], Assert.IsType<string>(file.Value.GetString())); }
            Fields(packet, "schemaVersion", "qualification", "mode", "baselineSha256", "executedSha256",
                "suiteSha256", "testsSha256", "tests", "failures", "errors", "skipped", "failedTests",
                "diagnosticBytes", "exitCode");
            Assert.Equal(1, packet.GetProperty("schemaVersion").GetInt32());
            Assert.False(packet.GetProperty("qualification").GetBoolean());
            Assert.Equal(mode, Text(packet, "mode"));
            Assert.Equal(control.GetProperty("exitCode").GetInt32(), packet.GetProperty("exitCode").GetInt32());
            Assert.Equal(mode == "mutation" ? 1 : 0, packet.GetProperty("failures").GetInt32());
            foreach (var key in new[] { "errors", "skipped", "diagnosticBytes" })
            { Assert.Equal(0, packet.GetProperty(key).GetInt32()); }
            testsCount ??= packet.GetProperty("tests").GetInt32();
            Assert.InRange(testsCount.Value, 1, 10000);
            Assert.Equal(testsCount.Value, packet.GetProperty("tests").GetInt32());
            Assert.Equal(Hash(source), Text(packet, "executedSha256"));
            original ??= source;
            var originalText = Encoding.UTF8.GetString(original);
            const string needle = "\n        elif entry.get(\"result\") != \"Passed\":\n";
            Assert.Equal(2, originalText.Split(needle, StringSplitOptions.None).Length);
            Assert.Equal(mode == "mutation" ? Encoding.UTF8.GetBytes(
                originalText.Replace(needle, "\n        elif False:\n", StringComparison.Ordinal)) : original, source);
            Assert.Equal(Hash(original), Text(packet, "baselineSha256"));
            Assert.Equal(Text(inputs.GetProperty("sourceManifest"), "scripts/metadata_evidence.py"), Hash(original));
            suiteHash ??= Text(packet, "suiteSha256");
            testsHash ??= Text(packet, "testsSha256");
            HashValue(testsHash);
            Assert.Equal(suiteHash, Text(packet, "suiteSha256"));
            Assert.Equal(testsHash, Text(packet, "testsSha256"));
            Assert.Equal(Text(inputs.GetProperty("sourceManifest"), "tests/tooling/test_metadata_evidence.py"), suiteHash);
            Assert.Equal(mode == "mutation" ? new[] { "test_metadata_evidence.MetadataEvidenceTests."
                + "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject" } : [],
                packet.GetProperty("failedTests").EnumerateArray().Select(value => value.GetString()).ToArray());
            previousSequence = sequence;
            previousEnd = end;
        }
        Assert.Equal(expected.Count, consumed.Count);
        var outputDirectory = InsideRoot(Text(context, "outputDirectory"));
        Assert.Equal(FileAttributes.Directory,
            File.GetAttributes(outputDirectory) & (FileAttributes.Directory | FileAttributes.ReparsePoint));
        var output = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            qualification = false,
            runId = Text(context, "runId"),
            attemptId = Text(context, "attemptId"),
            inputsSha256 = Text(context, "inputsSha256"),
            testIdentity = identity,
            files = consumed.ToDictionary(file => Hash(Encoding.UTF8.GetBytes(file.Key)), file => file.Value)
        });
        using var destination = new FileStream(Path.Combine(outputDirectory,
            "metadata-inventory-" + Hash(Encoding.UTF8.GetBytes(identity)) + ".json"), FileMode.CreateNew, FileAccess.Write);
        destination.Write(output);

        string InsideRoot(string path)
        {
            var absolute = Path.GetFullPath(Path.Combine(root, path));
            Assert.StartsWith(root + Path.DirectorySeparatorChar, absolute, StringComparison.Ordinal);
            return absolute;
        }

        byte[] Read(string relative, int limit)
        {
            Assert.False(Path.IsPathFullyQualified(relative));
            var path = InsideRoot(relative);
            Assert.True(expected.TryGetValue(path, out var hash));
            var bytes = ReadFile(path, Math.Min(limit, 16 * 1024 * 1024 - totalBytes));
            Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
            totalBytes += bytes.Length;
            Assert.Equal(hash, Hash(bytes));
            Assert.True(consumed.TryAdd(path, Hash(bytes)));
            return bytes;
        }

        JsonDocument ReadJson(string relative) => JsonDocument.Parse(Read(relative, 16 * 1024 * 1024));
    }
}
