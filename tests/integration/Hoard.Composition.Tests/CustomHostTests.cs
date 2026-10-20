using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using Hoard.Tests;

namespace Hoard.Composition.Tests;

public class CustomHostTests
{
    [Fact]
    public void Both_hosts_compile_with_only_the_artifact_reference_and_registration_changed()
    {
        var evidence = FoundationEvidence.Load();
        var hosts = evidence.GetProperty("hosts").EnumerateArray().ToArray();
        Assert.Equal(2, hosts.Length);
        var baseline = hosts[0].GetProperty("directory").GetString()!;
        var replacement = hosts[1].GetProperty("directory").GetString()!;
        Assert.Equal(File.ReadAllText(Path.Combine(baseline, "Program.cs"))
            .Replace("Artifact.One", "Artifact.Two").Replace("ArtifactOneProvider", "ArtifactTwoProvider"),
            File.ReadAllText(Path.Combine(replacement, "Program.cs")));
        Assert.Equal(File.ReadAllText(Path.Combine(baseline, "CustomHost.csproj")).Replace("Artifact.One", "Artifact.Two"),
            File.ReadAllText(Path.Combine(replacement, "CustomHost.csproj")));
        Assert.Equal(evidence.GetProperty("sourceHashesBefore").GetRawText(), evidence.GetProperty("sourceHashesAfter").GetRawText());
        foreach (var host in hosts)
        {
            var directory = host.GetProperty("directory").GetString()!;
            var project = XDocument.Load(Path.Combine(directory, "CustomHost.csproj"));
            Assert.Empty(project.Descendants("ProjectReference"));
            Assert.Empty(project.Descendants("Import"));
            Assert.Empty(project.Descendants("Compile"));
            Assert.Equal(5, project.Descendants("PackageReference").Count());
            var program = File.ReadAllText(Path.Combine(directory, "Program.cs"));
            Assert.DoesNotMatch(@"\.\s*(Build|Run|Start|Map\w*)\s*\(", program);
            Assert.DoesNotContain("InternalsVisibleTo", program);
            Assert.Equal(4, Regex.Matches(program, @"\.AddModule<").Count);
            Assert.True(File.Exists(host.GetProperty("assembly").GetString()));
            using var assets = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "obj/project.assets.json")));
            var libraries = assets.RootElement.GetProperty("libraries").EnumerateObject().ToArray();
            Assert.All(libraries, library => Assert.Equal("package", library.Value.GetProperty("type").GetString()));
            var artifact = Assert.Single(libraries, l => l.Name.StartsWith("Hoard.Fixtures.Artifact.", StringComparison.Ordinal));
            Assert.Contains(host.GetProperty("artifact").GetString()!, artifact.Name);
            FoundationEvidence.AssertLocalPackageProvenance(Path.Combine(directory, "obj/project.assets.json"));
        }
    }
}
