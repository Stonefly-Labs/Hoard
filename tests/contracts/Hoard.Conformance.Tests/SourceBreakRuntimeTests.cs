using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Conformance.Tests;

public sealed class SourceBreakRuntimeTests
{
    [Fact]
    public void Original_compiler_rejects_required_member_and_preserves_compatible_repair()
    {
        using var controlDocument = JsonDocument.Parse(Read("control.json"));
        using var sourcesDocument = JsonDocument.Parse(Read("sources.json", 16 * 1024 * 1024));
        using var inputsDocument = JsonDocument.Parse(Read("inputs.json", 16 * 1024 * 1024));
        using var negativeDocument = JsonDocument.Parse(Read("negative.json"));
        var control = controlDocument.RootElement;
        var sources = sourcesDocument.RootElement.GetProperty("sources");
        var negative = negativeDocument.RootElement;
        Assert.Equal(2, control.GetProperty("schemaVersion").GetInt32());
        Assert.False(control.GetProperty("qualification").GetBoolean());
        Assert.Equal("CS0535", control.GetProperty("compilerCode").GetString());
        Assert.Equal("RequiredContract.IProvider.Required()", control.GetProperty("symbol").GetString());
        Assert.Equal("restore-compatible-contract", control.GetProperty("repair").GetString());
        Assert.Equal(control.GetProperty("sourceFrameSha256").GetString(), Hash("sources.json"));
        Assert.Equal(control.GetProperty("inputsSha256").GetString(), Hash("inputs.json"));
        Assert.Equal(control.GetProperty("negativeExecutionSha256").GetString(), Hash("negative.json"));
        Assert.Equal(control.GetProperty("negativeSequence").GetInt64(), negative.GetProperty("sequence").GetInt64());
        Assert.Equal(1, negative.GetProperty("exitCode").GetInt32());
        Assert.Equal("None", negative.GetProperty("diagnosticCode").GetString());
        Assert.Equal("Exited", negative.GetProperty("groupState").GetString());
        Assert.Equal(negative.GetProperty("diagnosticsSha256").GetString(), Hash("diagnostics.jsonl"));
        Assert.Equal(control.GetProperty("inputsSha256").GetString(),
            negative.GetProperty("inputFiles").GetProperty("proofs/compatibility-source-break-inputs.json").GetString());
        Assert.Equal(control.GetProperty("contracts").GetProperty("New").GetString(),
            negative.GetProperty("inputFiles").GetProperty(
                "stores/compatibility-source-break/tests/fixtures/compatibility/RequiredMember/New/bin/Release/net10.0/RequiredContract.dll").GetString());
        var diagnostics = Encoding.UTF8.GetString(Read("diagnostics.jsonl"))
            .Split('\n', StringSplitOptions.RemoveEmptyEntries);
        Assert.NotEmpty(diagnostics);
        var codes = new List<int>();
        foreach (var line in diagnostics)
        {
            using var document = JsonDocument.Parse(line);
            Assert.Equal("build", document.RootElement.GetProperty("event").GetString());
            Assert.Equal("CommandFailed", document.RootElement.GetProperty("code").GetString());
            var value = document.RootElement.GetProperty("value").GetInt32();
            Assert.True(value is 0 or 535);
            codes.Add(value);
        }

        Assert.Contains(535, codes);
        const string fixture = "tests/fixtures/compatibility/RequiredMember/";
        var consumerSource = fixture + "Consumer/Provider.cs";
        Assert.Equal(control.GetProperty("consumerSourceSha256").GetString(), sources.GetProperty(consumerSource).GetString());
        Assert.Equal(sources.GetProperty(consumerSource).GetString(),
            inputsDocument.RootElement.GetProperty("sources").GetProperty(consumerSource).GetString());
        foreach (var variant in new[] { "Old", "New" })
        {
            Assert.Equal(control.GetProperty("contracts").GetProperty(variant).GetString(),
                Hash(variant + "/RequiredContract.dll"));
            Assert.Equal(control.GetProperty("contractPdbSha256").GetProperty(variant).GetString(),
                Hash(variant + "/RequiredContract.pdb"));
            VerifySource(variant + "/RequiredContract.dll", fixture + variant + "/Contract.cs", sources);
        }

        Assert.NotEqual(Hash("Old/RequiredContract.dll"), Hash("New/RequiredContract.dll"));
        foreach (var variant in new[] { "Consumer", "repair" })
        {
            Assert.Equal(control.GetProperty("consumerAssemblySha256").GetString(),
                Hash(variant + "/RequiredConsumer.dll"));
            Assert.Equal(control.GetProperty("consumerPdbSha256").GetString(),
                Hash(variant + "/RequiredConsumer.pdb"));
            VerifySource(variant + "/RequiredConsumer.dll", consumerSource, sources);
            using var context = new FixtureContext(Image("Old/RequiredContract.dll"));
            var consumer = context.LoadFromAssemblyPath(Image(variant + "/RequiredConsumer.dll"));
            var provider = Assert.IsType<Type>(consumer.GetType("Provider"), exactMatch: false);
            var contract = Assert.Single(provider.GetInterfaces());
            Assert.Equal("RequiredContract.IProvider", contract.FullName);
            Assert.Null(contract.GetMethod("Required"));
            Assert.Equal(Hash("Old/RequiredContract.dll"),
                ConformanceLoadedAssembly.CaptureContract(contract).AssemblySha256);
            var describe = Assert.IsType<MethodInfo>(provider.GetMethod("Describe"), exactMatch: false);
            var instance = Activator.CreateInstance(provider);
            Assert.NotNull(instance);
            Assert.Equal("Old source implementation", describe.Invoke(instance, null));
        }

        using var requiredContext = new FixtureContext(Image("New/RequiredContract.dll"));
        var requiredAssembly = requiredContext.LoadFromAssemblyPath(Image("New/RequiredContract.dll"));
        var required = Assert.IsType<Type>(requiredAssembly.GetType("RequiredContract.IProvider"), exactMatch: false);
        var member = Assert.IsType<MethodInfo>(required.GetMethod("Required"), exactMatch: false);
        Assert.Empty(member.GetParameters());
        Assert.Equal(typeof(string), member.ReturnType);
        Assert.Equal(Hash("New/RequiredContract.dll"), ConformanceLoadedAssembly.CaptureContract(required).AssemblySha256);
    }

    private static void VerifySource(string image, string source, JsonElement sources)
    {
        using var imageStream = File.OpenRead(Image(image));
        using var pe = new PEReader(imageStream);
        var entry = Assert.Single(pe.ReadDebugDirectory(), value => value.Type == DebugDirectoryEntryType.CodeView);
        var codeView = pe.ReadCodeViewDebugDirectoryData(entry);
        using var pdbStream = File.OpenRead(Image(Path.ChangeExtension(image, ".pdb")));
        using var provider = MetadataReaderProvider.FromPortablePdbStream(pdbStream);
        var reader = provider.GetMetadataReader();
        var header = reader.DebugMetadataHeader ?? throw new InvalidOperationException("ProofMismatch");
        var content = new BlobContentId(header.Id);
        Assert.Equal(codeView.Guid, content.Guid);
        Assert.Equal(entry.Stamp, content.Stamp);
        var document = Assert.Single(reader.Documents.Select(reader.GetDocument),
            value => reader.GetString(value.Name).Replace('\\', '/') == "/_/" + source);
        Assert.Equal(new Guid("8829d00f-11b8-4213-878b-770e8597ac16"), reader.GetGuid(document.HashAlgorithm));
        Assert.Equal(sources.GetProperty(source).GetString(), Convert.ToHexStringLower(reader.GetBlobBytes(document.Hash)));
    }

    private static string Image(string relative)
        => Path.Combine(AppContext.BaseDirectory, "source-break-fixtures", relative);

    private static byte[] Read(string relative, int maximum = 64 * 1024)
    {
        using var stream = File.OpenRead(Image(relative));
        Assert.InRange(stream.Length, 1, maximum);
        var bytes = new byte[checked((int)stream.Length)];
        stream.ReadExactly(bytes);
        Assert.Equal(-1, stream.ReadByte());
        return bytes;
    }

    private static string Hash(string relative)
    {
        using var stream = File.OpenRead(Image(relative));
        Assert.InRange(stream.Length, 1, 16 * 1024 * 1024);
        return Convert.ToHexStringLower(SHA256.HashData(stream));
    }

    private sealed class FixtureContext(string contract) : AssemblyLoadContext(isCollectible: true), IDisposable
    {
        protected override Assembly? Load(AssemblyName assemblyName)
            => assemblyName.Name == "RequiredContract" ? LoadFromAssemblyPath(contract) : null;

        public void Dispose() => Unload();
    }
}
