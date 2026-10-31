using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Conformance.Tests;

public sealed class CompatibilityBaselineTests
{
    [Theory]
    [InlineData("baseline", "BinaryContract.dll", "Old/Contract.cs")]
    [InlineData("broken", "BinaryContract.dll", "New/Contract.cs")]
    [InlineData("compatible", "BinaryContract.dll", "Old/Contract.cs")]
    [InlineData("consumer", "RetainedConsumer.dll", "Consumer/Program.cs")]
    public void Compiled_source_provenance_matches_actual_pe_pdb_and_frozen_historical_source(
        string variant, string name, string relative)
    {
        var image = Image(variant, name);
        using var imageStream = File.OpenRead(image);
        using var pe = new PEReader(imageStream);
        var entry = Assert.Single(pe.ReadDebugDirectory(), value => value.Type == DebugDirectoryEntryType.CodeView);
        var codeView = pe.ReadCodeViewDebugDirectoryData(entry);
        using var pdbStream = File.OpenRead(Path.ChangeExtension(image, ".pdb"));
        using var provider = MetadataReaderProvider.FromPortablePdbStream(pdbStream);
        var reader = provider.GetMetadataReader();
        var header = reader.DebugMetadataHeader ?? throw new InvalidOperationException("ProofMismatch");
        var content = new BlobContentId(header.Id);
        Assert.Equal(codeView.Guid, content.Guid);
        Assert.Equal(entry.Stamp, content.Stamp);
        var source = "tests/fixtures/compatibility/BinaryMemberRemoval/" + relative;
        var document = Assert.Single(reader.Documents.Select(reader.GetDocument),
            value => reader.GetString(value.Name).Replace('\\', '/') == "/_/" + source);
        Assert.Equal(new Guid("8829d00f-11b8-4213-878b-770e8597ac16"), reader.GetGuid(document.HashAlgorithm));
        using var frozenStream = typeof(CompatibilityBaselineTests).Assembly.GetManifestResourceStream(
            "Hoard.Conformance.CompatibilitySourceBaseline");
        using var frozen = JsonDocument.Parse(frozenStream ?? throw new InvalidOperationException("WitnessMissing"));
        Assert.Equal(frozen.RootElement.GetProperty("sources").GetProperty(source).GetString(),
            Convert.ToHexStringLower(reader.GetBlobBytes(document.Hash)));
    }

    [Theory]
    [InlineData("broken", false)]
    [InlineData("compatible", true)]
    public void Unchanged_retained_consumer_observes_actual_candidate_not_an_accidental_old_contract(
        string variant, bool compatible)
    {
        var consumer = Image("consumer", "RetainedConsumer.dll");
        var baseline = Image("baseline", "BinaryContract.dll");
        var candidate = Image(variant, "BinaryContract.dll");
        var consumerHash = Hash(consumer);
        var baselineHash = Hash(baseline);
        using var context = new FixtureContext(candidate);
        var retained = context.LoadFromAssemblyPath(consumer);
        var caller = Assert.IsType<Type>(retained.GetType("Caller"), exactMatch: false);
        var invoke = Assert.IsType<MethodInfo>(
            caller.GetMethod("Invoke", BindingFlags.Static | BindingFlags.NonPublic), exactMatch: false);

        if (compatible)
        {
            Assert.Equal("Old binary operation", invoke.Invoke(null, null));
        }
        else
        {
            var failure = Assert.Throws<TargetInvocationException>(() => invoke.Invoke(null, null));
            Assert.IsType<MissingMethodException>(failure.InnerException);
        }

        var loaded = Assert.Single(context.Assemblies, image => image.GetName().Name == "BinaryContract");
        var contract = Assert.IsType<Type>(loaded.GetType("BinaryContract.Api"), exactMatch: false);
        var observed = ConformanceLoadedAssembly.CaptureContract(contract);
        Assert.Equal(AssemblyName.GetAssemblyName(baseline).FullName, loaded.GetName().FullName);
        Assert.Equal(Hash(candidate), observed.AssemblySha256);
        Assert.NotEqual(baselineHash, observed.AssemblySha256);
        Assert.Equal(loaded.ManifestModule.ModuleVersionId, observed.ModuleVersionId);
        Assert.Equal(consumerHash, Hash(consumer));
        Assert.Equal(baselineHash, Hash(baseline));
    }

    [Fact]
    public void Loaded_baseline_capture_rejects_replacement_with_actual_same_version_candidate_bytes()
    {
        var baseline = Image("baseline", "BinaryContract.dll");
        var candidate = Image("broken", "BinaryContract.dll");
        var root = Path.Combine(AppContext.BaseDirectory, "compatibility-control-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var original = Path.Combine(root, "BinaryContract.dll");
            File.Copy(baseline, original);
            using var context = new FixtureContext(original);
            var loaded = context.LoadFromAssemblyPath(original);
            var contract = Assert.IsType<Type>(loaded.GetType("BinaryContract.Api"), exactMatch: false);
            var observed = ConformanceLoadedAssembly.CaptureContract(contract);
            Assert.Equal(Hash(baseline), observed.AssemblySha256);
            Assert.Equal(AssemblyName.GetAssemblyName(candidate).FullName, loaded.GetName().FullName);
            var replacement = Path.Combine(root, "replacement.dll");
            File.Copy(candidate, replacement);
            File.Move(replacement, original, overwrite: true);
            Assert.Equal(Hash(candidate), Hash(original));
            Assert.Equal("InputChanged", Assert.Throws<InvalidOperationException>(
                () => ConformanceLoadedAssembly.CaptureContract(contract)).Message);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    private static string Image(string variant, string name)
        => Path.Combine(AppContext.BaseDirectory, "compatibility-fixtures", variant, name);

    private static string Hash(string path)
        => Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));

    private sealed class FixtureContext(string candidate) : AssemblyLoadContext(isCollectible: true), IDisposable
    {
        protected override Assembly? Load(AssemblyName assemblyName)
            => assemblyName.Name == "BinaryContract" ? LoadFromAssemblyPath(candidate) : null;

        public void Dispose() => Unload();
    }
}
