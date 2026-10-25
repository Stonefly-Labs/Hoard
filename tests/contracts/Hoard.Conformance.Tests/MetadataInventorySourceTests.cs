using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using static Hoard.Conformance.Tests.MetadataRecoverySource;

namespace Hoard.Conformance.Tests;

public sealed class MetadataInventorySourceTests
{
    [Fact]
    public void Complete_inventory_graph_records_all_actual_consumed_bytes_once()
    {
        using var fixture = new SourceFixture();
        const string identity = "Hoard.Conformance.Tests.MetadataInventoryRuntimeTests.Sqlite_current_input_inventory_preserves_named_assertion_and_same_source_repair";
        MetadataInventorySource.Verify(fixture.ContextPath, identity);
        using var packet = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(fixture.Output).Single()));
        Assert.Equal(identity, packet.RootElement.GetProperty("testIdentity").GetString());
        Assert.Equal(14, packet.RootElement.GetProperty("files").EnumerateObject().Count());
        Assert.Throws<IOException>(() => MetadataInventorySource.Verify(fixture.ContextPath, identity));
    }

    [Fact]
    public void Rehashed_native_outputs_cannot_relabel_setup_failure_as_the_named_assertion()
    {
        using var fixture = new SourceFixture();
        var packetPath = SourceFixture.Prefix + "-mutation.json";
        var packet = JsonNode.Parse(fixture.Read(packetPath))!;
        packet["errors"] = 1;
        packet["failures"] = 0;
        fixture.Write(packetPath, packet);
        var nativePath = "proofs/execution-command-0002.json";
        var native = JsonNode.Parse(fixture.Read(nativePath))!;
        native["outputFiles"]![packetPath] = fixture.Files[fixture.Absolute(packetPath)];
        fixture.Write(nativePath, native);
        fixture.Graph["commands"]![1]!["executionSha256"] = fixture.Files[fixture.Absolute(nativePath)];
        fixture.SaveContext();
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => MetadataInventorySource.Verify(fixture.ContextPath, "model-only"));
        Assert.Empty(Directory.GetFiles(fixture.Output));
    }

    private sealed class SourceFixture : IDisposable
    {
        internal const string Prefix = "proofs/qualification-metadata-inventory";
        private readonly string root = Path.Combine(Path.GetTempPath(), "hoard-inventory-source-" + Guid.NewGuid());
        private readonly string run = Guid.NewGuid().ToString();
        private readonly string group = Guid.NewGuid().ToString();
        private readonly string attempt = Guid.NewGuid().ToString();
        private readonly string rootId = Guid.NewGuid().ToString();
        internal Dictionary<string, string> Files { get; } = new(StringComparer.Ordinal);
        internal JsonNode Graph { get; }
        internal string Output => Path.Combine(root, "output");
        internal string ContextPath => Path.Combine(root, "context.json");

        internal SourceFixture()
        {
            Directory.CreateDirectory(Path.Combine(root, "proofs"));
            Directory.CreateDirectory(Output);
            var original = Encoding.UTF8.GetBytes("# explicit decoder model, not runtime evidence\n"
                + "\n        elif entry.get(\"result\") != \"Passed\":\n");
            var names = new[] { "scripts/conformance_unit_checks.py", "scripts/conformance_sources.py",
                "scripts/conformance_case_catalog.py", "scripts/conformance_evidence.py",
                "scripts/conformance_execution.py", "scripts/conformance_lock_preparation.py",
                "scripts/metadata_evidence.py", "scripts/foundation_evidence.py", "scripts/lifecycle_evidence.py",
                "tests/tooling/test_metadata_evidence.py" };
            var sources = names.ToDictionary(name => name,
                name => name == "scripts/metadata_evidence.py" ? Hash(original) : new string('b', 64));
            var inputsPath = Prefix + "-native-inputs.json";
            Write(inputsPath, new
            {
                schemaVersion = 1,
                mode = "qualification",
                profileId = "metadata",
                runId = run,
                invocationGroupId = group,
                sourceManifest = sources
            });
            var inputHash = Files[Absolute(inputsPath)];
            var commands = new JsonArray();
            var index = 0;
            foreach (var mode in new[] { "baseline", "mutation", "repair" })
            {
                var sequence = ++index;
                var exit = mode == "mutation" ? 1 : 0;
                var source = mode == "mutation" ? Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(original).Replace(
                    "\n        elif entry.get(\"result\") != \"Passed\":\n", "\n        elif False:\n",
                    StringComparison.Ordinal)) : original;
                var sourcePath = Prefix + "-" + mode + ".py";
                File.WriteAllBytes(Absolute(sourcePath), source);
                Files[Absolute(sourcePath)] = Hash(source);
                var packetPath = Prefix + "-" + mode + ".json";
                Write(packetPath, new
                {
                    schemaVersion = 1,
                    qualification = false,
                    mode,
                    baselineSha256 = Hash(original),
                    executedSha256 = Hash(source),
                    suiteSha256 = sources["tests/tooling/test_metadata_evidence.py"],
                    testsSha256 = new string('c', 64),
                    tests = 17,
                    failures = exit,
                    errors = 0,
                    skipped = 0,
                    failedTests = exit == 1 ? new[] { "test_metadata_evidence.MetadataEvidenceTests."
                        + "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject" } : [],
                    diagnosticBytes = 0,
                    exitCode = exit
                });
                var control = new
                {
                    schemaVersion = 1,
                    sequence,
                    childPid = 200 + sequence,
                    childStartSha256 = new string('d', 64),
                    startedMs = sequence * 1000,
                    endedMs = sequence * 1000 + 100,
                    exitCode = exit,
                    diagnosticCode = "None",
                    groupState = "Exited",
                    scope = "recovery"
                };
                var controlPath = $"proofs/recovery-command-{sequence:D4}.json";
                Write(controlPath, control);
                var native = JsonSerializer.SerializeToNode(control)!;
                native["runId"] = run;
                native["rootId"] = rootId;
                native["argvSha256"] = new string('e', 64);
                native["cwdSha256"] = new string('f', 64);
                native["controlRecordSha256"] = Files[Absolute(controlPath)];
                var inputFiles = sources.ToDictionary(pair => "snapshot/" + pair.Key, pair => pair.Value);
                inputFiles[inputsPath] = inputHash;
                native["inputFiles"] = JsonSerializer.SerializeToNode(inputFiles);
                native["outputFiles"] = JsonSerializer.SerializeToNode(new Dictionary<string, string>
                {
                    [packetPath] = Files[Absolute(packetPath)],
                    [sourcePath] = Files[Absolute(sourcePath)]
                });
                var nativePath = $"proofs/execution-command-{sequence:D4}.json";
                Write(nativePath, native);
                commands.Add(new JsonObject
                {
                    ["mode"] = mode,
                    ["sequence"] = sequence,
                    ["controllerSha256"] = Files[Absolute(controlPath)],
                    ["executionSha256"] = Files[Absolute(nativePath)]
                });
            }
            Graph = new JsonObject
            {
                ["schemaVersion"] = 1,
                ["qualification"] = false,
                ["runId"] = run,
                ["invocationGroupId"] = group,
                ["inputsSha256"] = inputHash,
                ["scriptPath"] = "snapshot/scripts/conformance_unit_checks.py",
                ["inputsPath"] = inputsPath,
                ["commands"] = commands
            };
            SaveContext();
        }

        internal string Absolute(string path) => Path.Combine(root, path);
        internal byte[] Read(string path) => File.ReadAllBytes(Absolute(path));

        internal void Write(string path, object value)
        {
            var raw = JsonSerializer.SerializeToUtf8Bytes(value);
            File.WriteAllBytes(Absolute(path), raw);
            Files[Absolute(path)] = Hash(raw);
        }

        internal void SaveContext()
        {
            Write(Prefix + "-native-executions.json", Graph);
            File.WriteAllBytes(ContextPath, JsonSerializer.SerializeToUtf8Bytes(new
            {
                schemaVersion = 1,
                runId = run,
                invocationGroupId = group,
                attemptId = attempt,
                rootId,
                inputsSha256 = Files[Absolute(Prefix + "-native-inputs.json")],
                rootPath = root,
                graphPath = Prefix + "-native-executions.json",
                outputDirectory = Output,
                files = Files
            }));
        }

        public void Dispose() => Directory.Delete(root, recursive: true);
    }
}
