using System.Text.Json;
using System.Xml.Linq;
using Hoard.Tests;

namespace Hoard.Composition.Tests;

public class CoreIndependenceTests
{
    [Fact]
    public void Isolated_core_has_only_abstractions_and_framework_reachable()
    {
        var core = FoundationEvidence.Load().GetProperty("core");
        var directory = core.GetProperty("directory").GetString()!;
        Assert.Equal(["Hoard.Abstractions", "Hoard.Core"],
            Directory.GetDirectories(Path.Combine(directory, "src")).Select(Path.GetFileName).Order());
        var project = XDocument.Load(Path.Combine(directory, "src/Hoard.Core/Hoard.Core.csproj"));
        Assert.Empty(project.Descendants("PackageReference"));
        Assert.Single(project.Descendants("ProjectReference"));
        using var assets = JsonDocument.Parse(File.ReadAllText(core.GetProperty("assets").GetString()!));
        var library = Assert.Single(assets.RootElement.GetProperty("libraries").EnumerateObject());
        Assert.Equal("Hoard.Abstractions/0.1.0", library.Name);
        Assert.Equal("project", library.Value.GetProperty("type").GetString());
        Assert.True(File.Exists(core.GetProperty("assembly").GetString()));
    }
}
