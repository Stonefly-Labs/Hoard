using System.IO.Compression;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Hoard.Conformance.Tests;

public sealed class RetainedBinaryRuntimeTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    [Fact]
    public void Original_retained_consumers_bind_sealed_pe_pdb_and_actual_loaded_candidate_identities()
    {
        using var stream = File.OpenRead(Path.Combine(AppContext.BaseDirectory, "retained-compatibility-fixture.zip"));
        Assert.InRange(stream.Length, 1, 16 * 1024 * 1024);
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read);
        Assert.InRange(archive.Entries.Count, 1, 128);
        Assert.Equal(archive.Entries.Count, archive.Entries.Select(entry => entry.FullName).Distinct().Count());
        Assert.InRange(archive.Entries.Sum(entry => entry.Length), 1, 16 * 1024 * 1024);
        var files = archive.Entries.ToDictionary(entry => entry.FullName, Read, StringComparer.Ordinal);
        using var controlDocument = JsonDocument.Parse(files["control.json"]);
        using var observerDocument = JsonDocument.Parse(files["observer-inputs.json"]);
        using var sourceDocument = JsonDocument.Parse(files["source-inputs.json"]);
        using var baselineDocument = JsonDocument.Parse(files["baselines.json"]);
        var control = controlDocument.RootElement;
        var observer = observerDocument.RootElement;
        var source = sourceDocument.RootElement;
        var baselines = baselineDocument.RootElement;
        Assert.Equal(2, control.GetProperty("schemaVersion").GetInt32());
        Assert.Equal(3, baselines.GetProperty("schemaVersion").GetInt32());
        Assert.Equal("retained-compatibility", Text(control, "mode"));
        foreach (var value in new[] { control, observer, source, baselines })
        {
            Assert.False(value.GetProperty("qualification").GetBoolean());
        }

        var seal = Hash(files["baselines.json"]);
        Assert.Equal(seal, Text(control, "baselineSealSha256"));
        Assert.Equal(seal, Text(observer, "baselineSealSha256"));
        Assert.Equal(seal, Text(source, "baselineSealSha256"));
        Assert.Equal(Digest(observer.GetProperty("sources")), Text(observer, "candidateSourceSha256"));
        Assert.Equal(Digest(observer.GetProperty("sources")),
            Digest(source.GetProperty("sources").GetProperty("candidate-source-manifest")));
        var expected = new HashSet<string>(StringComparer.Ordinal)
        {
            "control.json", "observer-inputs.json", "source-inputs.json", "baselines.json"
        };
        var preparation = control.GetProperty("observerPreparation");
        Assert.Equal(Hash(files["observer-inputs.json"]), Text(preparation, "inputFrameSha256"));
        Assert.Equal(Text(control, "observerSha256"), Text(preparation, "assemblySha256"));
        const string observerName = "Hoard.Conformance.Compatibility.Observer";
        const string observerProject = "tests/fixtures/conformance/Compatibility/Observer/Observer.csproj";
        const string observerLock = "tests/fixtures/conformance/Compatibility/Observer/packages.lock.json";
        Assert.Equal("stores/retained-compatibility-observer/" + observerName + ".dll",
            Text(preparation, "assemblyPath"));
        var observerImage = Image(files, expected, Text(preparation, "assemblySha256"), ".dll");
        var observerPdb = Image(files, expected, Text(preparation, "pdbSha256"), ".pdb");
        Pair(observerImage, observerPdb, observerName);
        long sequence = 0;
        double ended = 0;
        string? runId = null, rootId = null;
        var commands = preparation.GetProperty("commands");
        Assert.InRange(commands.GetArrayLength(), 1, 2);
        for (var index = 0; index < commands.GetArrayLength(); index++)
        {
            var record = Record(files, expected, commands[index], ref sequence, ref ended, ref runId, ref rootId);
            var inputs = record.GetProperty("inputFiles");
            Assert.Equal(4, inputs.EnumerateObject().Count());
            Assert.Equal(Hash(files["observer-inputs.json"]), Text(inputs, "proofs/retained-observer-inputs.json"));
            Assert.Equal(Text(observer, "configurationSha256"), Text(inputs, "stores/candidate.NuGet.Config"));
            Assert.Equal(Text(observer.GetProperty("sources"), observerProject), Text(inputs, "stores/snapshot/" + observerProject));
            Assert.Equal(Text(observer.GetProperty("sources"), observerLock), Text(inputs, "stores/snapshot/" + observerLock));
            if (index == commands.GetArrayLength() - 1)
            {
                var outputs = record.GetProperty("outputFiles");
                Assert.Equal(2, outputs.EnumerateObject().Count());
                Assert.Equal(Hash(observerImage), Text(outputs, "proofs/retained-observer-output/" + observerName + ".dll"));
                Assert.Equal(Hash(observerPdb), Text(outputs, "proofs/retained-observer-output/" + observerName + ".pdb"));
            }
            else
            {
                Assert.False(record.TryGetProperty("outputFiles", out _));
            }
        }

        string[] scenarios =
        [
            "registration", "lifecycle", "configuration", "metadata-marker", "artifact-marker",
            "memory", "sqlite", "local", "object"
        ];
        string[] platform = ["Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Application"];
        var rows = control.GetProperty("scenarios");
        Assert.Equal(scenarios.Length, rows.GetArrayLength());
        for (var index = 0; index < scenarios.Length; index++)
        {
            var scenario = scenarios[index];
            var row = rows[index];
            Assert.Equal(scenario, Text(row, "scenario"));
            var scope = index >= 5 ? "operational-consumer" : index >= 3 ? "marker-only" : "inherited-api";
            Assert.Equal(scope, Text(row, "scope"));
            Assert.False(row.GetProperty("commonSuiteExecuted").GetBoolean());
            using var requestDocument = Frame(files, expected, row, scenario, "request", "requestSha256");
            using var stagedDocument = Frame(files, expected, row, scenario, "staged", "stagedSha256");
            using var observationDocument = Frame(files, expected, row, scenario, "observation", "observationSha256");
            var request = requestDocument.RootElement;
            var staged = stagedDocument.RootElement;
            var observation = observationDocument.RootElement;
            foreach (var frame in new[] { request, staged, observation })
            {
                Assert.Equal(scenario, Text(frame, "scenario"));
            }

            Assert.Equal(seal, Text(staged, "baselineSealSha256"));
            Assert.Equal(scope, Text(staged, "scope"));
            Assert.False(staged.GetProperty("commonSuiteExecuted").GetBoolean());
            var baselineId = index < 5 ? scenario : "f06";
            Assert.Equal(baselineId, Text(staged, "baselineId"));
            var baseline = Assert.Single(baselines.GetProperty("entries").EnumerateArray(),
                entry => Text(entry, "id") == baselineId);
            var assembly = Text(staged, "assembly");
            var name = Path.GetFileNameWithoutExtension(assembly);
            var original = Assert.Single(baseline.GetProperty("binaries").EnumerateObject(),
                entry => entry.Name.EndsWith("/" + assembly, StringComparison.Ordinal));
            var prefix = original.Name[..^assembly.Length];
            var frozen = staged.GetProperty("frozenFiles");
            Assert.Equal(Digest(frozen), Digest(JsonSerializer.SerializeToElement(
                baseline.GetProperty("binaries").EnumerateObject()
                    .Where(entry => entry.Name.StartsWith(prefix, StringComparison.Ordinal))
                    .ToDictionary(entry => entry.Name[prefix.Length..], entry => entry.Value.GetString()),
                JsonOptions)));
            var stagedFiles = staged.GetProperty("stagedFiles");
            var candidate = staged.GetProperty("candidateAssemblies");
            Assert.Equal(4, candidate.EnumerateObject().Count());
            Assert.Equal(4, staged.GetProperty("candidatePackages").EnumerateObject().Count());
            var overlay = Map(frozen);
            foreach (var item in platform)
            {
                var hashed = Text(candidate, item + ".dll");
                overlay[item + ".dll"] = hashed;
                Image(files, expected, hashed, ".dll");
                Assert.Equal(Text(source.GetProperty("candidatePackages"), item + ".0.1.0.nupkg"),
                    Text(staged.GetProperty("candidatePackages"), item + ".0.1.0.nupkg"));
            }

            Assert.Equal(overlay.OrderBy(entry => entry.Key, StringComparer.Ordinal),
                Map(stagedFiles).OrderBy(entry => entry.Key, StringComparer.Ordinal));
            Assert.Equal(Text(frozen, assembly), Text(stagedFiles, assembly));
            var consumerImage = Image(files, expected, Text(frozen, assembly), ".dll");
            var consumerPdb = Image(files, expected, Text(frozen, name + ".pdb"), ".pdb");
            Pair(consumerImage, consumerPdb, name);
            var runtime = "stores/retained-compatibility-" + scenario;
            Assert.Equal(runtime, Text(staged, "runtimePath"));
            var requestImages = request.GetProperty("images").EnumerateArray().ToArray();
            var requested = requestImages.ToDictionary(
                image => Path.GetFileNameWithoutExtension(Text(image, "path")), image => Text(image, "sha256"),
                StringComparer.Ordinal);
            foreach (var image in requestImages)
            {
                var imageName = Path.GetFileName(Text(image, "path"));
                Assert.Equal(runtime + "/" + imageName, Text(image, "path"));
                Assert.Equal(Text(stagedFiles, imageName), Text(image, "sha256"));
            }

            Assert.False(observation.GetProperty("qualification").GetBoolean());
            Assert.Equal("None", Text(observation, "code"));
            var loaded = observation.GetProperty("loaded").EnumerateArray().ToArray();
            Assert.Equal(row.GetProperty("loadedAssemblies").GetInt32(), loaded.Length);
            var names = loaded.Select(image => Text(image, "name")).ToArray();
            Assert.Equal(names.Distinct().Order(StringComparer.Ordinal), names);
            foreach (var required in request.GetProperty("required").EnumerateArray())
            {
                Assert.Contains(required.GetString(), names);
            }

            Assert.Contains(name, names);
            Assert.Contains("Hoard.Abstractions", names);
            foreach (var image in loaded)
            {
                var loadedName = Text(image, "name");
                var hashed = Text(image, "sha256");
                Assert.Equal(requested[loadedName], hashed);
                var bytes = Image(files, expected, hashed, ".dll");
                using var peStream = new MemoryStream(bytes, writable: false);
                using var pe = new PEReader(peStream);
                Assert.True(pe.HasMetadata);
                var reader = pe.GetMetadataReader();
                Assert.True(reader.IsAssembly);
                Assert.Equal(loadedName, reader.GetString(reader.GetAssemblyDefinition().Name));
                var mvid = reader.GetGuid(reader.GetModuleDefinition().Mvid);
                Assert.NotEqual(Guid.Empty, mvid);
                Assert.Equal(mvid.ToString("D"), Text(image, "moduleVersionId"));
            }

            var record = Record(files, expected, row, ref sequence, ref ended, ref runId, ref rootId);
            var inputFiles = record.GetProperty("inputFiles");
            var namespacePath = "proofs/retained-compatibility-" + scenario;
            Assert.Equal(4, inputFiles.EnumerateObject().Count());
            Assert.Equal(Hash(observerImage), Text(inputFiles, Text(preparation, "assemblyPath")));
            Assert.Equal(Hash(consumerImage), Text(inputFiles, runtime + "/" + assembly));
            Assert.Equal(Text(row, "requestSha256"), Text(inputFiles, namespacePath + "-request.json"));
            Assert.Equal(Text(row, "stagedSha256"), Text(inputFiles, namespacePath + "-staged.json"));
            var outputFiles = record.GetProperty("outputFiles");
            Assert.Single(outputFiles.EnumerateObject());
            Assert.Equal(Text(row, "observationSha256"), Text(outputFiles, namespacePath + "-observation.json"));
            Assert.Equal(namespacePath + "-observation.json", Text(request, "outputPath"));
        }

        Assert.Equal(expected.Order(StringComparer.Ordinal), files.Keys.Order(StringComparer.Ordinal));
    }

    private static JsonDocument Frame(
        Dictionary<string, byte[]> files, HashSet<string> expected, JsonElement row,
        string scenario, string kind, string field)
    {
        var name = $"scenarios/{scenario}/{kind}.json";
        Assert.True(expected.Add(name));
        Assert.Equal(Text(row, field), Hash(files[name]));
        return JsonDocument.Parse(files[name]);
    }

    private static JsonElement Record(
        Dictionary<string, byte[]> files, HashSet<string> expected, JsonElement declared,
        ref long sequence, ref double ended, ref string? runId, ref string? rootId)
    {
        var current = declared.GetProperty("sequence").GetInt64();
        Assert.True(current > sequence);
        sequence = current;
        var name = $"commands/execution-command-{sequence:0000}.json";
        Assert.True(expected.Add(name));
        Assert.Equal(Text(declared, "executionSha256"), Hash(files[name]));
        using var document = JsonDocument.Parse(files[name]);
        var record = document.RootElement;
        Assert.Equal(1, record.GetProperty("schemaVersion").GetInt32());
        Assert.Equal(sequence, record.GetProperty("sequence").GetInt64());
        Assert.Equal(0, record.GetProperty("exitCode").GetInt32());
        Assert.Equal("None", Text(record, "diagnosticCode"));
        Assert.Equal("Exited", Text(record, "groupState"));
        Assert.Equal("ordinary", Text(record, "scope"));
        Assert.True(record.GetProperty("childPid").GetInt64() > 0);
        Assert.NotEqual(new string('0', 64), Text(record, "childStartSha256"));
        runId ??= Text(record, "runId");
        rootId ??= Text(record, "rootId");
        Assert.Equal(runId, Text(record, "runId"));
        Assert.Equal(rootId, Text(record, "rootId"));
        var started = record.GetProperty("startedMs").GetDouble();
        var finished = record.GetProperty("endedMs").GetDouble();
        Assert.True(double.IsFinite(started) && started >= ended);
        Assert.True(double.IsFinite(finished) && finished >= started);
        ended = finished;
        return record.Clone();
    }

    private static byte[] Image(Dictionary<string, byte[]> files, HashSet<string> expected, string hashed, string suffix)
    {
        var name = "images/" + hashed + suffix;
        expected.Add(name);
        var bytes = files[name];
        Assert.Equal(hashed, Hash(bytes));
        return bytes;
    }

    private static void Pair(byte[] image, byte[] pdb, string name)
    {
        using var imageStream = new MemoryStream(image, writable: false);
        using var pdbStream = new MemoryStream(pdb, writable: false);
        SourceImageProvenance.Verify(imageStream, pdbStream, (assembly, _) =>
            Assert.Equal(name, assembly.GetString(assembly.GetAssemblyDefinition().Name)));
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

    private static Dictionary<string, string> Map(JsonElement value)
        => value.EnumerateObject().ToDictionary(row => row.Name, row => Assert.IsType<string>(row.Value.GetString()),
            StringComparer.Ordinal);

    private static string Digest(JsonElement value)
        => Hash(JsonSerializer.SerializeToUtf8Bytes(new SortedDictionary<string, string>(Map(value),
            StringComparer.Ordinal), JsonOptions));

    private static string Text(JsonElement value, string name) => Assert.IsType<string>(value.GetProperty(name).GetString());
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
}
