using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Logging;

namespace Hoard.Conformance.Tests;

public sealed class RuntimeDiscoveryTests
{
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
