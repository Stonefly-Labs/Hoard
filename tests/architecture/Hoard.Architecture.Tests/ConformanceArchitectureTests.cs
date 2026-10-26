using System.Text.Json;
using System.Xml.Linq;
using Mono.Cecil;

namespace Hoard.Architecture.Tests;

public sealed class ConformanceArchitectureTests
{
    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public void Actual_declared_and_compiled_graph_paths_reject_test_sdk_but_permit_driver_sdk(
        bool transitive, bool compiled)
    {
        using var forbidden = new GraphFixture("Hoard.Testing.Conformance", transitive, compiled);
        using var inspected = InspectionEvidence.Load(forbidden.Graph);
        DependencyGraphInspector.Read(inspected);
        Assert.Contains(DependencyGraphInspector.Inspect(inspected), violation =>
            violation.RuleId == "ARCH-008" && violation.Source == "MetadataProvider"
            && violation.Target == "Hoard.Testing.Conformance"
            && violation.Path == (transitive
                ? "MetadataProvider -> DriverHelper -> Hoard.Testing.Conformance"
                : "MetadataProvider -> Hoard.Testing.Conformance"));
        using var permitted = new GraphFixture("Vendor.Driver", transitive, compiled);
        using var counterpart = InspectionEvidence.Load(permitted.Graph);
        DependencyGraphInspector.Read(counterpart);
        Assert.Empty(DependencyGraphInspector.Inspect(counterpart));
    }

    [Theory]
    [InlineData("Abstractions", "ARCH-001")]
    [InlineData("Core", "ARCH-002")]
    [InlineData("Hosting", "ARCH-008")]
    [InlineData("Application", "ARCH-008")]
    [InlineData("Protocol", "ARCH-008")]
    [InlineData("Metadata", "ARCH-008")]
    [InlineData("Artifact", "ARCH-008")]
    [InlineData("Identity", "ARCH-008")]
    [InlineData("Host", "ARCH-008")]
    public void Test_sdk_is_not_a_production_driver_sdk(string source, string rule)
    {
        var boundary = Enum.Parse<BoundaryOwnership>(source);
        foreach (var package in new[] { "Hoard.Testing.Conformance", "hoard.testing.conformance" })
        {
            Assert.Equal(rule, DependencyGraphInspector.Rule(
                boundary, BoundaryOwnership.Sdk, 2, false, package));
            Assert.Equal(boundary == BoundaryOwnership.Core ? "ARCH-003" : rule,
                DependencyGraphInspector.Rule(boundary, BoundaryOwnership.Sdk, 3, false, package));
        }
    }

    [Theory]
    [InlineData("Metadata")]
    [InlineData("Artifact")]
    [InlineData("Identity")]
    public void Driver_sdk_permission_is_preserved_without_allowing_the_test_suite(string source)
    {
        var boundary = Enum.Parse<BoundaryOwnership>(source);
        Assert.Null(DependencyGraphInspector.Rule(boundary, BoundaryOwnership.Sdk, 2, false, "Vendor.Driver"));
        Assert.Equal("ARCH-008", DependencyGraphInspector.Rule(
            boundary, BoundaryOwnership.Sdk, 2, false, "Hoard.Testing.Conformance"));
    }

    [Theory]
    [InlineData("Sdk")]
    [InlineData("Helper")]
    public void Explicit_test_owners_can_consume_the_test_suite(string source) =>
        Assert.Null(DependencyGraphInspector.Rule(Enum.Parse<BoundaryOwnership>(source),
            BoundaryOwnership.Sdk, 2, false, "Hoard.Testing.Conformance"));

    [Theory]
    [InlineData("Bcl")]
    [InlineData("Abstractions")]
    [InlineData("Helper")]
    public void Test_sdk_cannot_be_reclassified_to_bypass_the_boundary(string ownership) =>
        Assert.Throws<InspectionException>(() => DependencyGraphInspector.Rule(
            BoundaryOwnership.Metadata, Enum.Parse<BoundaryOwnership>(ownership), 2, false,
            "Hoard.Testing.Conformance"));

    private sealed class GraphFixture : IDisposable
    {
        private readonly string root = Path.Combine(Path.GetTempPath(), "hoard-conformance-graph-" + Guid.NewGuid().ToString("N"));
        public JsonElement Graph { get; }

        public GraphFixture(string sdk, bool transitive, bool compiled)
        {
            Directory.CreateDirectory(root);
            var dependencies = new Dictionary<string, string[]>
            {
                [sdk] = [],
                ["DriverHelper"] = [sdk],
                ["MetadataProvider"] = [transitive ? "DriverHelper" : sdk]
            };
            var ownership = dependencies.Keys.ToDictionary(id => id, id => id == "MetadataProvider" ? "Metadata" : "Sdk");
            var projects = new List<object>();
            foreach (var (id, targets) in dependencies)
            {
                var selected = new HashSet<string>();
                var pending = new Stack<string>(targets);
                while (pending.TryPop(out var target))
                {
                    if (!selected.Add(target)) { continue; }
                    foreach (var dependency in dependencies[target]) { pending.Push(dependency); }
                }
                using var assembly = AssemblyDefinition.CreateAssembly(
                    new AssemblyNameDefinition(id, new(0, 1, 0, 0)), id, ModuleKind.Dll);
                if (compiled)
                {
                    foreach (var target in targets)
                    { assembly.MainModule.AssemblyReferences.Add(new AssemblyNameReference(target, new(0, 1, 0, 0))); }
                }
                assembly.Write(Path.Combine(root, id + ".dll"));
                new XElement("Project", new XElement("ItemGroup",
                    targets.Select(target => new XElement("ProjectReference", new XAttribute("Include", target + ".csproj")))))
                    .Save(Path.Combine(root, id + ".csproj"));
                var libraries = selected.ToDictionary(
                    other => other + "/0.1.0", other => new { type = "project", path = other + ".csproj" });
                var targetsModel = dependencies.Where(pair => selected.Contains(pair.Key)).ToDictionary(
                    pair => pair.Key + "/0.1.0", pair => new
                    {
                        type = "project",
                        dependencies = pair.Value.ToDictionary(target => target, _ => "0.1.0")
                    });
                var assets = new
                {
                    targets = new Dictionary<string, object> { ["net10.0"] = targetsModel },
                    libraries,
                    project = new
                    {
                        frameworks = new Dictionary<string, object>
                        {
                            ["net10.0"] = new
                            {
                                dependencies = new Dictionary<string, object>(),
                                frameworkReferences = new Dictionary<string, object> { ["Microsoft.NETCore.App"] = new { } }
                            }
                        }
                    }
                };
                File.WriteAllText(Path.Combine(root, id + ".assets.json"), JsonSerializer.Serialize(assets));
                var references = selected
                    .Select(other => new Dictionary<string, string> { ["Identity"] = Path.Combine(root, other + ".dll") }).ToList();
                references.Add(new()
                {
                    ["Identity"] = typeof(object).Assembly.Location,
                    ["FrameworkReferenceName"] = "Microsoft.NETCore.App",
                    ["NuGetPackageId"] = "Microsoft.NETCore.App.Ref"
                });
                projects.Add(new
                {
                    id,
                    project = Path.Combine(root, id + ".csproj"),
                    assets = Path.Combine(root, id + ".assets.json"),
                    assembly = Path.Combine(root, id + ".dll"),
                    sources = Array.Empty<string>(),
                    references
                });
            }
            using var document = JsonDocument.Parse(JsonSerializer.Serialize(new { ownership, projects }));
            Graph = document.RootElement.Clone();
        }

        public void Dispose() => Directory.Delete(root, recursive: true);
    }
}
