using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Hoard.Conformance.Tests;

public sealed class MetadataRecoverySourceTests
{
    [Fact]
    public void Complete_current_input_graph_records_the_bytes_actually_read()
    {
        using var fixture = new SourceFixture();
        MetadataRecoverySource.Verify(fixture.ContextPath);
        var packet = Directory.GetFiles(fixture.Output).Single();
        using var document = JsonDocument.Parse(File.ReadAllBytes(packet));
        Assert.Equal(fixture.Files.Count, document.RootElement.GetProperty("files").EnumerateObject().Count());
        Assert.Equal(MetadataRecoverySource.Identity, document.RootElement.GetProperty("testIdentity").GetString());
        Assert.Throws<IOException>(() => MetadataRecoverySource.Verify(fixture.ContextPath));
    }

    [Theory]
    [InlineData("foreign-input")]
    [InlineData("omitted-command")]
    [InlineData("wrong-control")]
    [InlineData("unread-file")]
    public void Self_consistent_file_hashes_do_not_replace_graph_validation(string mutation)
    {
        using var fixture = new SourceFixture();
        switch (mutation)
        {
            case "foreign-input":
                fixture.Graph["inputsSha256"] = new string('a', 64);
                break;
            case "omitted-command":
                fixture.Commands.RemoveAt(30);
                break;
            case "wrong-control":
                fixture.Commands[1]!["controllerSha256"] = new string('a', 64);
                break;
            case "unread-file":
                fixture.Write("proofs/unconsumed.json", new { value = 1 });
                break;
        }
        fixture.SaveContext();
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => MetadataRecoverySource.Verify(fixture.ContextPath));
        Assert.Empty(Directory.GetFiles(fixture.Output));
    }

    private sealed class SourceFixture : IDisposable
    {
        private readonly string root = Path.Combine(Path.GetTempPath(), "hoard-metadata-source-" + Guid.NewGuid());
        private readonly string run = Guid.NewGuid().ToString();
        private readonly string group = Guid.NewGuid().ToString();
        private readonly string attempt = Guid.NewGuid().ToString();
        private readonly string rootId = Guid.NewGuid().ToString();
        private readonly string inputsPath = "proofs/qualification-sqlite-recovery-native-inputs.json";
        private readonly string graphPath = "proofs/qualification-sqlite-recovery-native-executions.json";
        private readonly string sourcePath = "proofs/qualification-sqlite-recovery.json";
        private readonly string assembly = "candidate/CrashRunner.dll";
        private readonly string inputsHash;

        internal SourceFixture()
        {
            Directory.CreateDirectory(Path.Combine(root, "proofs"));
            Directory.CreateDirectory(Output);
            Write(inputsPath, new
            {
                schemaVersion = 1,
                mode = "qualification",
                profileId = "metadata",
                runId = run,
                invocationGroupId = group,
                runtimeAssemblies = new Dictionary<string, string> { [assembly] = new string('b', 64) }
            });
            inputsHash = Files[Path.Combine(root, inputsPath)];
            var barriers = new JsonArray();
            var sequence = 0;
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
                    foreach (var mode in new[] { "seed", "run", "recover" })
                    { hashes.Add(AddCommand(++sequence, mode + "-" + kind, names[index], mode == "run" ? offset + index : null)); }
                    barriers.Add(new JsonObject
                    {
                        ["barrierId"] = names[index],
                        ["value"] = offset + index,
                        ["seedSha256"] = hashes[0],
                        ["controllerSha256"] = hashes[1],
                        ["readbackSha256"] = hashes[2],
                        ["childStartSha256"] = new string('c', 64)
                    });
                }
            }
            var walkthrough = AddCommand(++sequence, "recovery-walkthrough", "none", null);
            Write(sourcePath, new
            {
                qualification = false,
                mode = "metadata-recovery",
                code = "None",
                inputsSha256 = inputsHash,
                barriers,
                walkthroughSha256 = walkthrough
            });
            Graph = new JsonObject
            {
                ["schemaVersion"] = 1,
                ["qualification"] = false,
                ["runId"] = run,
                ["invocationGroupId"] = group,
                ["inputsSha256"] = inputsHash,
                ["assemblyPath"] = assembly,
                ["inputsPath"] = inputsPath,
                ["commands"] = Commands,
                ["sourceReceiptSha256"] = Files[Path.Combine(root, sourcePath)]
            };
            SaveContext();
        }

        internal string Output => Path.Combine(root, "output");
        internal string ContextPath => Path.Combine(root, "context.json");
        internal Dictionary<string, string> Files { get; } = new(StringComparer.Ordinal);
        internal JsonArray Commands { get; } = new();
        internal JsonObject Graph { get; }

        internal void Write(string relative, object value)
        {
            var path = Path.Combine(root, relative);
            var bytes = JsonSerializer.SerializeToUtf8Bytes(value);
            File.WriteAllBytes(path, bytes);
            Files[path] = Convert.ToHexStringLower(SHA256.HashData(bytes));
        }

        internal void SaveContext()
        {
            Write(graphPath, Graph);
            File.WriteAllBytes(ContextPath, JsonSerializer.SerializeToUtf8Bytes(new
            {
                schemaVersion = 1,
                runId = run,
                invocationGroupId = group,
                attemptId = attempt,
                rootId,
                inputsSha256 = inputsHash,
                rootPath = root,
                graphPath,
                sourcePath,
                outputDirectory = Output,
                files = Files
            }));
        }

        private string AddCommand(int sequence, string mode, string barrierId, int? barrier)
        {
            var control = new JsonObject
            {
                ["schemaVersion"] = 1,
                ["sequence"] = sequence,
                ["childPid"] = sequence + 100,
                ["childStartSha256"] = new string('c', 64),
                ["startedMs"] = sequence * 10,
                ["endedMs"] = sequence * 10 + 3,
                ["exitCode"] = barrier is null ? 0 : -9,
                ["diagnosticCode"] = "None",
                ["groupState"] = "Exited",
                ["scope"] = "recovery"
            };
            if (barrier is not null)
            {
                control["barrier"] = new JsonObject
                { ["value"] = barrier, ["observedMs"] = sequence * 10 + 1, ["signalMs"] = sequence * 10 + 2 };
            }
            var controlPath = $"proofs/recovery-command-{sequence:D4}.json";
            Write(controlPath, control);
            var hash = Files[Path.Combine(root, controlPath)];
            var native = (JsonObject)control.DeepClone();
            native.Remove("barrier");
            native["runId"] = run;
            native["rootId"] = rootId;
            native["argvSha256"] = new string('d', 64);
            native["cwdSha256"] = new string('e', 64);
            native["controlRecordSha256"] = hash;
            native["inputFiles"] = new JsonObject { [assembly] = new string('b', 64), [inputsPath] = inputsHash };
            var nativePath = $"proofs/execution-command-{sequence:D4}.json";
            Write(nativePath, native);
            Commands.Add(new JsonObject
            {
                ["mode"] = mode,
                ["barrierId"] = barrierId,
                ["sequence"] = sequence,
                ["controllerSha256"] = hash,
                ["executionSha256"] = Files[Path.Combine(root, nativePath)]
            });
            return hash;
        }

        public void Dispose() => Directory.Delete(root, recursive: true);
    }
}
