using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Logging;

namespace Hoard.Conformance.Tests;

public sealed class RuntimeDiscoveryTests
{
    [Theory]
    [InlineData("none")]
    [InlineData("changed-image")]
    [InlineData("changed-request")]
    [InlineData("duplicate-image")]
    [InlineData("escaped-image")]
    public void Discovery_request_binds_all_images_without_expanding_parent_command_limits(string mutation)
    {
        using var owned = new RuntimeLoggerTests.OwnedInput();
        var image = new RuntimeFile("test-assembly", "tests.dll",
            Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(owned.AssemblyPath))));
        var request = new RuntimeDiscoveryRequest(["Hoard.Frozen.Check"],
            mutation == "duplicate-image" ? [image, image] : [image]);
        if (mutation == "escaped-image")
        { request.Assemblies[0] = image with { Path = "../tests.dll" }; }
        var bytes = JsonSerializer.SerializeToUtf8Bytes(request, RuntimeLoggerTests.Json);
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        File.WriteAllBytes(Path.Combine(owned.Root, "discovery-request.json"), bytes);
        if (mutation == "changed-image") { File.AppendAllText(owned.AssemblyPath, "changed"); }
        if (mutation == "changed-request") { File.AppendAllText(Path.Combine(owned.Root, "discovery-request.json"), " "); }
        if (mutation != "none")
        {
            Assert.Throws<InvalidDataException>(() =>
                RuntimeCaseDiscovery.ReadRequest(owned.Root, "discovery-request.json", digest));
            return;
        }
        Assert.Single(RuntimeCaseDiscovery.ReadRequest(owned.Root, "discovery-request.json", digest).Assemblies);
        Assert.Throws<InvalidDataException>(() => RuntimeCaseDiscovery.CreateOutput(owned.Root, "../outside.json"));
        using (RuntimeCaseDiscovery.CreateOutput(owned.Root, "discovery-output.json")) { }
        Assert.Throws<IOException>(() => RuntimeCaseDiscovery.CreateOutput(owned.Root, "discovery-output.json"));
    }

    [Theory]
    [InlineData("none", ConformanceDiagnosticCode.None)]
    [InlineData("missing-method", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("duplicate", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("aborted", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("wrong-count", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("foreign-source", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("changed-assembly", ConformanceDiagnosticCode.InputChanged)]
    [InlineData("unknown-message", ConformanceDiagnosticCode.UnknownDiagnostic)]
    public void Safe_discovery_requires_complete_exact_actual_cases(string mutation, ConformanceDiagnosticCode expected)
    {
        using var owned = new RuntimeLoggerTests.OwnedInput();
        const string method = "Hoard.Frozen.Check";
        var collector = new RuntimeCaseDiscovery(owned.AssemblyPath,
            mutation == "missing-method" ? [method, "Hoard.Frozen.Other"] : [method]);
        var tests = Enumerable.Range(0, 2).Select(_ => new TestCase(method,
            new Uri("executor://xunit/VsTestRunner2/netcore/"), owned.AssemblyPath)
        { Id = Guid.NewGuid(), DisplayName = method + "(value: \"/private/canary\"...)" }).ToArray();
        if (mutation == "duplicate") { tests[1].Id = tests[0].Id; }
        if (mutation == "foreign-source") { tests[1].Source = owned.OwnerPath; }
        collector.HandleDiscoveredTests(tests);
        if (mutation == "changed-assembly") { File.AppendAllText(owned.AssemblyPath, "changed"); }
        if (mutation == "unknown-message")
        { collector.HandleLogMessage(TestMessageLevel.Warning, "private/canary"); }
        collector.HandleDiscoveryComplete(mutation == "wrong-count" ? 3 : 2, null, mutation == "aborted");
        Assert.Equal(expected, collector.Diagnostic);
        if (expected != ConformanceDiagnosticCode.None)
        { Assert.Throws<InvalidDataException>(() => collector.Cases); return; }
        Assert.Equal(2, collector.Cases.Count);
        Assert.Equal(2, collector.Cases.Select(entry => entry.TestIdentity).Distinct(StringComparer.Ordinal).Count());
        Assert.All(collector.Cases, entry =>
        {
            Assert.StartsWith(method + "(testCaseSha256: \"", entry.TestIdentity, StringComparison.Ordinal);
            Assert.DoesNotContain("private", entry.TestIdentity, StringComparison.Ordinal);
            Assert.DoesNotContain("canary", entry.TestIdentity, StringComparison.Ordinal);
        });
    }
}
