using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Hoard.Conformance.Tests;

public sealed class SourceRecipeRuntimeTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    [Fact]
    public void Original_source_recipes_bind_candidate_compilers_and_actual_pe_pdb_source_documents()
    {
        using var stream = File.OpenRead(Path.Combine(AppContext.BaseDirectory, "source-compatibility-fixture.zip"));
        Assert.InRange(stream.Length, 1, 16 * 1024 * 1024);
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read);
        Assert.InRange(archive.Entries.Count, 1, 128);
        Assert.Equal(archive.Entries.Count, archive.Entries.Select(entry => entry.FullName).Distinct().Count());
        Assert.InRange(archive.Entries.Sum(entry => entry.Length), 1, 16 * 1024 * 1024);
        var files = archive.Entries.ToDictionary(entry => entry.FullName, Read, StringComparer.Ordinal);
        using var controlDocument = JsonDocument.Parse(files["control.json"]);
        using var inputsDocument = JsonDocument.Parse(files["inputs.json"]);
        using var policyStream = typeof(SourceRecipeRuntimeTests).Assembly.GetManifestResourceStream(
            "Hoard.Conformance.SourceRecipePolicy");
        using var policyDocument = JsonDocument.Parse(
            policyStream ?? throw new InvalidOperationException("WitnessMissing"));
        var control = controlDocument.RootElement;
        var inputs = inputsDocument.RootElement;
        var policy = policyDocument.RootElement;
        Assert.Equal(2, control.GetProperty("schemaVersion").GetInt32());
        Assert.Equal(1, inputs.GetProperty("schemaVersion").GetInt32());
        Assert.False(control.GetProperty("qualification").GetBoolean());
        Assert.False(inputs.GetProperty("qualification").GetBoolean());
        Assert.Equal("source-compatibility", control.GetProperty("mode").GetString());
        Assert.Equal(control.GetProperty("inputFrameSha256").GetString(), Hash(files["inputs.json"]));
        Assert.Equal(control.GetProperty("baselineSealSha256").GetString(),
            inputs.GetProperty("baselineSealSha256").GetString());
        var policyHash = Hash(JsonSerializer.SerializeToUtf8Bytes(new
        {
            baselineRevision = policy.GetProperty("baselineRevision").GetString(),
            qualification = false,
            recipes = policy.GetProperty("recipes").EnumerateArray().Select(row => new
            {
                project = row.GetProperty("project").GetString(),
                role = row.GetProperty("role").GetString(),
                sourceKind = row.GetProperty("sourceKind").GetString()
            }),
            schemaVersion = 1
        }, JsonOptions));
        Assert.Equal(policyHash, control.GetProperty("recipeSha256").GetString());
        Assert.Equal(policyHash, inputs.GetProperty("recipeSha256").GetString());
        Assert.Equal(SourceDigest(control.GetProperty("candidatePackages")),
            SourceDigest(inputs.GetProperty("candidatePackages")));
        var recipes = control.GetProperty("recipes");
        Assert.Equal(24, recipes.GetArrayLength());
        Assert.Equal(24, policy.GetProperty("recipes").GetArrayLength());
        var expected = new HashSet<string>(StringComparer.Ordinal) { "control.json", "inputs.json" };
        long previousSequence = 0;
        double previousEnd = 0;
        string? runId = null, rootId = null;
        for (var index = 0; index < recipes.GetArrayLength(); index++)
        {
            var row = recipes[index];
            var declared = policy.GetProperty("recipes")[index];
            foreach (var key in new[] { "project", "role", "sourceKind" })
            {
                Assert.Equal(declared.GetProperty(key).GetString(), row.GetProperty(key).GetString());
            }

            var project = Text(row, "project");
            var kind = Text(row, "sourceKind");
            var name = Text(row, "assemblyName");
            var sources = inputs.GetProperty("sources").GetProperty(kind);
            Assert.Equal(SourceDigest(sources), row.GetProperty("sourceSha256").GetString());
            Assert.Equal($"stores/source-compatibility-images/recipe-{index:00}",
                row.GetProperty("outputDirectory").GetString());
            var image = $"images/{index:00}/{name}.dll";
            var pdb = $"images/{index:00}/{name}.pdb";
            Assert.True(expected.Add(image));
            Assert.True(expected.Add(pdb));
            Assert.Equal(row.GetProperty("assemblySha256").GetString(), Hash(files[image]));
            Assert.Equal(row.GetProperty("pdbSha256").GetString(), Hash(files[pdb]));
            using var imageStream = new MemoryStream(files[image], writable: false);
            using var pdbStream = new MemoryStream(files[pdb], writable: false);
            SourceImageProvenance.Verify(imageStream, pdbStream, (assembly, reader) =>
            {
                Assert.True(assembly.IsAssembly);
                Assert.Equal(name, assembly.GetString(assembly.GetAssemblyDefinition().Name));
                var authored = new HashSet<string>(StringComparer.Ordinal);
                var projectDirectory = project[..project.LastIndexOf('/')];
                var generatedPrefix = projectDirectory + "/obj/Release/net10.0/";
                var generated = new[]
                {
                    ".NETCoreApp,Version=v10.0.AssemblyAttributes.cs",
                    Path.GetFileNameWithoutExtension(project) + ".AssemblyInfo.cs",
                    Path.GetFileNameWithoutExtension(project) + ".GlobalUsings.g.cs"
                };
                foreach (var handle in reader.Documents)
                {
                    var document = reader.GetDocument(handle);
                    var path = reader.GetString(document.Name).Replace('\\', '/');
                    Assert.StartsWith("/_/", path, StringComparison.Ordinal);
                    var source = path[3..];
                    Assert.Equal(new Guid("8829d00f-11b8-4213-878b-770e8597ac16"),
                        reader.GetGuid(document.HashAlgorithm));
                    if (sources.TryGetProperty(source, out var frozen))
                    {
                        Assert.Equal(frozen.GetString(), Convert.ToHexStringLower(reader.GetBlobBytes(document.Hash)));
                        authored.Add(source);
                    }
                    else
                    {
                        Assert.StartsWith(generatedPrefix, source, StringComparison.Ordinal);
                        Assert.Contains(source[generatedPrefix.Length..], generated);
                    }
                }

                Assert.Contains(authored, source => source.StartsWith(projectDirectory + "/", StringComparison.Ordinal));
            });
            var commands = row.GetProperty("commands");
            Assert.InRange(commands.GetArrayLength(), 1, 3);
            for (var step = 0; step < commands.GetArrayLength(); step++)
            {
                var command = commands[step];
                var sequence = command.GetProperty("sequence").GetInt64();
                Assert.True(sequence > previousSequence);
                previousSequence = sequence;
                var commandName = $"commands/execution-command-{sequence:0000}.json";
                Assert.True(expected.Add(commandName));
                Assert.Equal(command.GetProperty("executionSha256").GetString(), Hash(files[commandName]));
                using var recordDocument = JsonDocument.Parse(files[commandName]);
                var record = recordDocument.RootElement;
                Assert.Equal(1, record.GetProperty("schemaVersion").GetInt32());
                Assert.Equal(sequence, record.GetProperty("sequence").GetInt64());
                Assert.Equal(0, record.GetProperty("exitCode").GetInt32());
                Assert.Equal("None", record.GetProperty("diagnosticCode").GetString());
                Assert.Equal("Exited", record.GetProperty("groupState").GetString());
                Assert.Equal("ordinary", record.GetProperty("scope").GetString());
                Assert.True(record.GetProperty("childPid").GetInt64() > 0);
                Assert.NotEqual(new string('0', 64), Text(record, "childStartSha256"));
                runId ??= Text(record, "runId");
                rootId ??= Text(record, "rootId");
                Assert.Equal(runId, Text(record, "runId"));
                Assert.Equal(rootId, Text(record, "rootId"));
                var started = record.GetProperty("startedMs").GetDouble();
                var ended = record.GetProperty("endedMs").GetDouble();
                Assert.True(double.IsFinite(started) && started >= previousEnd);
                Assert.True(double.IsFinite(ended) && ended >= started);
                previousEnd = ended;
                var original = record.GetProperty("inputFiles");
                Assert.Equal(4, original.EnumerateObject().Count());
                Assert.Equal(control.GetProperty("inputFrameSha256").GetString(),
                    original.GetProperty("proofs/source-compatibility-inputs.json").GetString());
                Assert.Equal(inputs.GetProperty("configurationSha256").GetString(),
                    original.GetProperty("stores/source-compatibility.NuGet.Config").GetString());
                Assert.Equal(sources.GetProperty(project).GetString(),
                    original.GetProperty("stores/source-compatibility-" + kind + "/" + project).GetString());
                var directory = project[..project.LastIndexOf('/')];
                var lockPath = directory + "/packages.lock.json";
                if (!sources.TryGetProperty(lockPath, out var lockHash))
                {
                    lockPath = directory + "/Baseline/packages.lock.json";
                    lockHash = sources.GetProperty(lockPath);
                }

                var preparations = row.GetProperty("lockPreparations");
                Assert.InRange(preparations.GetArrayLength(), 0, 1);
                var selectedLock = lockPath;
                var selectedHash = Assert.IsType<string>(lockHash.GetString());
                if (preparations.GetArrayLength() == 1)
                {
                    var prepared = preparations[0];
                    Assert.Equal(lockPath, prepared.GetProperty("originalLock").GetString());
                    Assert.Equal(selectedHash, prepared.GetProperty("originalSha256").GetString());
                    selectedLock = Text(prepared, "preparedLock");
                    selectedHash = Text(prepared, "preparedSha256");
                }

                Assert.Equal(selectedHash,
                    original.GetProperty("stores/source-compatibility-" + kind + "/" + selectedLock).GetString());
                if (step == commands.GetArrayLength() - 1)
                {
                    var output = record.GetProperty("outputFiles");
                    Assert.Equal(2, output.EnumerateObject().Count());
                    Assert.Equal(Hash(files[image]),
                        output.GetProperty($"proofs/source-recipe-output-{index:00}/{name}.dll").GetString());
                    Assert.Equal(Hash(files[pdb]),
                        output.GetProperty($"proofs/source-recipe-output-{index:00}/{name}.pdb").GetString());
                }
                else
                {
                    Assert.False(record.TryGetProperty("outputFiles", out _));
                }
            }
        }

        Assert.Equal(expected.Order(StringComparer.Ordinal), files.Keys.Order(StringComparer.Ordinal));
    }

    private static byte[] Read(ZipArchiveEntry entry)
    {
        Assert.InRange(entry.Length, 1, 16 * 1024 * 1024);
        using var stream = entry.Open();
        var bytes = new byte[checked((int)entry.Length)];
        stream.ReadExactly(bytes);
        Assert.Equal(-1, stream.ReadByte());
        return bytes;
    }

    private static string Text(JsonElement value, string name)
        => Assert.IsType<string>(value.GetProperty(name).GetString());

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private static string SourceDigest(JsonElement sources)
        => Hash(JsonSerializer.SerializeToUtf8Bytes(new SortedDictionary<string, string>(
            sources.EnumerateObject().ToDictionary(row => row.Name, row => Assert.IsType<string>(row.Value.GetString())),
            StringComparer.Ordinal), JsonOptions));
}
