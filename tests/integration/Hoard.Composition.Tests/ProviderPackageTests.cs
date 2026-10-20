using System.IO.Compression;
using System.Text.Json;
using System.Xml.Linq;
using Hoard.Tests;

namespace Hoard.Composition.Tests;

public class ProviderPackageTests
{
    [Fact]
    public void Five_packages_build_independently_and_match_resolved_dependencies()
    {
        var providers = FoundationEvidence.Load().GetProperty("providers").EnumerateArray().ToArray();
        Assert.Equal(5, providers.Length);
        Assert.Equal(5, providers.Select(p => p.GetProperty("id").GetString()).Distinct().Count());
        Assert.Equal(4, providers.Select(p => p.GetProperty("family").GetString()).Distinct().Count());
        foreach (var provider in providers)
        {
            var directory = provider.GetProperty("directory").GetString()!;
            var project = XDocument.Load(Directory.GetFiles(directory, "*.csproj").Single());
            Assert.Empty(project.Descendants("ProjectReference"));
            Assert.Empty(project.Descendants("Import"));
            Assert.Empty(project.Descendants("Compile"));
            Assert.All(project.Descendants("PackageReference"), reference =>
                Assert.Equal("Hoard.Abstractions", reference.Attribute("Include")!.Value));
            Assert.DoesNotContain("InternalsVisibleTo", string.Join("\n", Directory.GetFiles(directory, "*.cs").Select(File.ReadAllText)));
            Assert.False(File.Exists(Path.Combine(directory, "Directory.Build.props")));
            using var assets = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "obj/project.assets.json")));
            Assert.Equal(["Hoard.Abstractions/0.1.0"], assets.RootElement.GetProperty("libraries").EnumerateObject().Select(p => p.Name));
            using var package = ZipFile.OpenRead(provider.GetProperty("package").GetString()!);
            using var nuspecStream = package.Entries.Single(e => e.FullName.EndsWith(".nuspec", StringComparison.Ordinal)).Open();
            var nuspec = XDocument.Load(nuspecStream);
            Assert.Equal(["Hoard.Abstractions"], nuspec.Descendants().Where(e => e.Name.LocalName == "dependency")
                .Select(e => e.Attribute("id")!.Value).Distinct());
            Assert.True(File.Exists(provider.GetProperty("consumerAssembly").GetString()));
            Assert.True(File.Exists(Path.Combine(Path.GetDirectoryName(Path.GetDirectoryName(
                provider.GetProperty("consumerAssets").GetString()!))!, "packages.lock.json")));
            Assert.True(File.Exists(provider.GetProperty("assembly").GetString()));
            FoundationEvidence.AssertLocalPackageProvenance(Path.Combine(directory, "obj/project.assets.json"));
            FoundationEvidence.AssertLocalPackageProvenance(provider.GetProperty("consumerAssets").GetString()!);
        }
    }
}
