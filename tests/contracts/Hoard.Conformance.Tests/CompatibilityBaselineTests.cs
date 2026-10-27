using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Conformance.Tests;

public sealed class CompatibilityBaselineTests
{
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
