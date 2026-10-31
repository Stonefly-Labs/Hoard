using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Tests;

namespace Hoard.Architecture.Tests;

public class InspectionFailureTests
{
    [Fact]
    public void Captured_inspection_inputs_are_the_actual_json_xml_and_pe_bytes_without_private_paths()
    {
        using var fixture = new InputFixture();
        var text = fixture.Write("canary-private-input.txt", "canary-private-content");
        var xml = fixture.Write("canary-private-project.xml", "<Project><Item>one</Item></Project>");
        var assemblyPath = typeof(InspectionFailureTests).Assembly.Location;
        var expected = new Dictionary<string, string>
        {
            [text] = InputFixture.Hash(text),
            [xml] = InputFixture.Hash(xml),
            [assemblyPath] = InputFixture.Hash(assemblyPath)
        };
        using var capture = InspectionInput.Begin(
            Guid.NewGuid(), Guid.NewGuid(), "Inspection.Unit", new string('a', 64), expected, fixture.Root);
        expected.Clear();
        Assert.Equal("canary-private-content", InspectionInput.ReadAllText(text));
        Assert.Equal("one", InspectionInput.LoadXml(xml).Root!.Element("Item")!.Value);
        using (var assembly = InspectionInput.ReadAssembly(assemblyPath))
        {
            Assert.Equal(typeof(InspectionFailureTests).Module.ModuleVersionId, assembly.MainModule.Mvid);
        }
        capture.Complete();
        var packet = File.ReadAllText(Assert.Single(Directory.GetFiles(fixture.Root, "inspection-*.json")));
        Assert.DoesNotContain("canary-private", packet);
        Assert.DoesNotContain(fixture.Root, packet);
        Assert.DoesNotContain(assemblyPath, packet);
        using var document = JsonDocument.Parse(packet);
        var files = document.RootElement.GetProperty("files");
        Assert.Equal(3, files.EnumerateObject().Count());
        foreach (var path in new[] { text, xml, assemblyPath })
        {
            var id = Convert.ToHexStringLower(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(path)));
            Assert.Equal(InputFixture.Hash(path), files.GetProperty(id).GetString());
        }
        Assert.Throws<InspectionException>(() => capture.Complete());
        Assert.Single(Directory.GetFiles(fixture.Root, "inspection-*.json"));
    }

    [Theory]
    [InlineData("missing", "EvidenceIncomplete")]
    [InlineData("unselected", "ProofMismatch")]
    [InlineData("changed", "InputChanged")]
    [InlineData("oversized", "OutputLimitExceeded")]
    public void Incomplete_changed_or_unselected_inspection_inputs_cannot_publish_a_receipt(string mutation, string code)
    {
        using var fixture = new InputFixture();
        var path = fixture.Write("selected.txt", "original");
        using var capture = InspectionInput.Begin(
            Guid.NewGuid(), Guid.NewGuid(), "Inspection.Unit", new string('a', 64),
            new Dictionary<string, string> { [path] = InputFixture.Hash(path) }, fixture.Root);
        var error = Assert.Throws<InspectionException>(() =>
        {
            if (mutation == "missing") { capture.Complete(); }
            else if (mutation == "unselected")
            {
                InspectionInput.ReadAllText(fixture.Write("foreign.txt", "original"));
            }
            else if (mutation == "changed")
            {
                Assert.Equal("original", InspectionInput.ReadAllText(path));
                File.WriteAllText(path, "replacement");
                Assert.Equal("original", InspectionInput.ReadAllText(path));
                capture.Complete();
            }
            else
            {
                using (var file = new FileStream(path, FileMode.Open, FileAccess.Write))
                {
                    file.SetLength(64 * 1024 * 1024 + 1);
                }
                InspectionInput.ReadAllText(path);
            }
        });
        Assert.Equal("INSPECTION: " + code, error.Message);
        Assert.Empty(Directory.GetFiles(fixture.Root, "inspection-*.json"));
    }

    [Fact]
    public void A_failed_or_abandoned_capture_cannot_publish_or_contaminate_the_next_inspection()
    {
        using var fixture = new InputFixture();
        var path = fixture.Write("selected.txt", "selected");
        var expected = new Dictionary<string, string> { [path] = InputFixture.Hash(path) };
        using (var abandoned = InspectionInput.Begin(
            Guid.NewGuid(), Guid.NewGuid(), "Inspection.Unit", new string('a', 64), expected, fixture.Root))
        {
            Assert.Equal("selected", InspectionInput.ReadAllText(path));
        }
        Assert.Empty(Directory.GetFiles(fixture.Root, "inspection-*.json"));
        using (var failed = InspectionInput.Begin(
            Guid.NewGuid(), Guid.NewGuid(), "Inspection.Unit", new string('a', 64), expected, fixture.Root))
        {
            Assert.Equal("selected", InspectionInput.ReadAllText(path));
            Assert.Throws<InspectionException>(() => InspectionInput.ReadAllText(fixture.Write("foreign.txt", "foreign")));
            Assert.Throws<InspectionException>(() => failed.Complete());
        }
        Assert.Empty(Directory.GetFiles(fixture.Root, "inspection-*.json"));
        Assert.Equal("foreign", InspectionInput.ReadAllText(Path.Combine(fixture.Root, "foreign.txt")));
        using (var fresh = InspectionInput.Begin(
            Guid.NewGuid(), Guid.NewGuid(), "Inspection.Unit", new string('b', 64), expected, fixture.Root))
        {
            Assert.Equal("selected", InspectionInput.ReadAllText(path));
            fresh.Complete();
        }
        Assert.Single(Directory.GetFiles(fixture.Root, "inspection-*.json"));
    }

    [Theory]
    [InlineData("duplicate")]
    [InlineData("unknown")]
    [InlineData("reduced")]
    [InlineData("foreign")]
    [InlineData("changed")]
    public void Requested_context_is_closed_and_binds_the_exact_inspection(string mutation)
    {
        using var fixture = new InputFixture();
        var path = fixture.Write("selected.txt", "selected");
        var model = new JsonObject
        {
            ["schemaVersion"] = 1,
            ["runId"] = Guid.NewGuid().ToString(),
            ["attemptId"] = Guid.NewGuid().ToString(),
            ["inputsSha256"] = new string('a', 64),
            ["outputDirectory"] = fixture.Root,
            ["cases"] = new JsonObject { ["Inspection.Unit"] = new JsonObject { [path] = InputFixture.Hash(path) } }
        };
        if (mutation == "unknown") { model["unrecognized"] = true; }
        if (mutation == "reduced") { model.Remove("runId"); }
        if (mutation == "foreign") { model["cases"]!.AsObject().Remove("Inspection.Unit"); }
        if (mutation == "changed") { File.WriteAllText(path, "replacement"); }
        var json = model.ToJsonString();
        if (mutation == "duplicate") { json = json.Insert(1, "\"schemaVersion\":1,"); }
        var error = Assert.Throws<InspectionException>(() =>
        {
            using var capture = InspectionInput.BeginFromContext("Inspection.Unit", System.Text.Encoding.UTF8.GetBytes(json));
            InspectionInput.ReadAllText(path);
            capture.Complete();
        });
        Assert.Equal("INSPECTION: " + (mutation == "changed" ? "InputChanged" : "ProofMismatch"), error.Message);
        Assert.Empty(Directory.GetFiles(fixture.Root, "inspection-*.json"));
    }

    [Fact]
    public void A_selected_context_preserves_its_attempt_and_empty_literal_input_assignment()
    {
        using var fixture = new InputFixture();
        var run = Guid.NewGuid();
        var attempt = Guid.NewGuid();
        var data = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            runId = run,
            attemptId = attempt,
            inputsSha256 = new string('a', 64),
            outputDirectory = fixture.Root,
            cases = new Dictionary<string, object> { ["Inspection.Unit"] = new Dictionary<string, string>() }
        });
        using var capture = InspectionInput.BeginFromContext("Inspection.Unit", data);
        using var literal = JsonDocument.Parse("""{"runtimeTargets":{"native/sqlite.dll":{"assetType":"native"}}}""");
        Assert.True(InspectionEvidence.HasNoManagedAssets(literal.RootElement));
        capture.Complete();
        using var packet = JsonDocument.Parse(File.ReadAllText(Assert.Single(Directory.GetFiles(fixture.Root, "inspection-*.json"))));
        Assert.Equal(run, packet.RootElement.GetProperty("runId").GetGuid());
        Assert.Equal(attempt, packet.RootElement.GetProperty("attemptId").GetGuid());
        Assert.Empty(packet.RootElement.GetProperty("files").EnumerateObject());
    }

    private sealed class InputFixture : IDisposable
    {
        public string Root { get; } = Path.Combine(Path.GetTempPath(), "hoard-inspection-" + Guid.NewGuid().ToString("N"));

        public InputFixture() => Directory.CreateDirectory(Root);
        public string Write(string name, string value)
        {
            var path = Path.Combine(Root, name);
            File.WriteAllText(path, value);
            return path;
        }

        public static string Hash(string path) => Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));
        public void Dispose() => Directory.Delete(Root, recursive: true);
    }

    [Theory]
    [InlineData("platform")]
    [InlineData("provider:Hoard.Fixtures.Protocol")]
    [InlineData("provider:Hoard.Fixtures.Metadata")]
    [InlineData("provider:Hoard.Fixtures.Artifact.One")]
    [InlineData("provider:Hoard.Fixtures.Artifact.Two")]
    [InlineData("provider:Hoard.Fixtures.Identity")]
    [InlineData("host:One")]
    [InlineData("host:Two")]
    public void Omitting_any_required_real_scan_is_an_error(string identity)
    {
        var graphs = JsonNode.Parse(FoundationEvidence.Load().GetProperty("realArchitecture").GetRawText())!.AsArray();
        graphs.Remove(graphs.Single(graph => graph!["scanId"]!.GetValue<string>() == identity));
        using var document = JsonDocument.Parse(graphs.ToJsonString());
        var error = Assert.Throws<InspectionException>(() => ArchitectureInspection.InspectRealGraphs(document.RootElement));
        Assert.Contains(identity, error.Message);
    }

    [Theory]
    [InlineData("assembly")]
    [InlineData("assets")]
    [InlineData("references")]
    [InlineData("ownership")]
    [InlineData("duplicate")]
    [InlineData("slices")]
    [InlineData("unresolved")]
    [InlineData("empty")]
    public void Incomplete_inputs_are_inspection_errors_not_clean_scans(string failure)
    {
        var graph = JsonNode.Parse(FoundationEvidence.Load().GetProperty("architecture").GetProperty("permitted").GetRawText())!;
        var projects = graph["projects"]!.AsArray();
        switch (failure)
        {
            case "assembly":
                projects[0]!["assembly"] = "/missing/foundation-input.dll";
                break;
            case "assets":
                projects[0]!["assets"] = "/missing/project.assets.json";
                break;
            case "references":
                projects[0]!["references"] = new JsonArray();
                break;
            case "ownership":
                graph["ownership"]!.AsObject().Remove("Metadata");
                break;
            case "duplicate":
                projects.Add(projects[0]!.DeepClone());
                break;
            case "slices":
                foreach (var project in projects)
                {
                    project!["sources"] = new JsonArray();
                }
                break;
            case "unresolved":
                projects[0]!["references"]![0]!["Identity"] = "/missing/System.Runtime.dll";
                break;
            case "empty":
                graph["projects"] = new JsonArray();
                break;
        }
        using var document = JsonDocument.Parse(graph.ToJsonString());
        var error = Assert.Throws<InspectionException>(() => ArchitectureInspection.Inspect(document.RootElement));
        Assert.StartsWith("INSPECTION:", error.Message);
    }
}
