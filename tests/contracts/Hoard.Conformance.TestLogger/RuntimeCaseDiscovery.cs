using System.Text;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Client;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Logging;

namespace Hoard.Conformance.TestLogger;

public sealed record RuntimeDiscoveredCase(string TestIdentity, string FullyQualifiedName);

public sealed class RuntimeCaseDiscovery : ITestDiscoveryEventsHandler
{
    private readonly string assembly;
    private readonly string assemblySha256;
    private readonly HashSet<string> methods;
    private readonly Dictionary<string, RuntimeDiscoveredCase> cases = new(StringComparer.Ordinal);
    private int observed;
    private bool completed;

    public ConformanceDiagnosticCode Diagnostic { get; private set; }
    public IReadOnlyList<RuntimeDiscoveredCase> Cases => completed && Diagnostic == ConformanceDiagnosticCode.None
        ? cases.Values.OrderBy(entry => entry.TestIdentity, StringComparer.Ordinal).ToArray()
        : throw RuntimeSafety.Error("EvidenceIncomplete");

    public RuntimeCaseDiscovery(string assembly, IEnumerable<string> methods)
    {
        this.assembly = Path.GetFullPath(assembly);
        RuntimeSafety.CheckLinks(this.assembly);
        assemblySha256 = RuntimeSafety.FileHash(this.assembly);
        this.methods = new(methods, StringComparer.Ordinal);
        RuntimeSafety.Require(this.methods.Count is > 0 and <= RuntimeSafety.MaxTests);
        foreach (var method in this.methods) { RuntimeSafety.IdentityPair(method, method); }
    }

    public void HandleDiscoveredTests(IEnumerable<TestCase>? discoveredTests)
    {
        if (Diagnostic != ConformanceDiagnosticCode.None) { return; }
        try
        {
            RuntimeSafety.Require(!completed && discoveredTests is not null, "EvidenceIncomplete");
            foreach (var test in discoveredTests)
            {
                RuntimeSafety.Require(++observed <= RuntimeSafety.MaxTests, "OutputLimitExceeded");
                if (!methods.Contains(test.FullyQualifiedName)) { continue; }
                RuntimeSafety.Require(test.Source is { Length: > 0 and <= 4096 }
                    && Path.GetFullPath(test.Source) == assembly, "ProofMismatch");
                RuntimeSafety.Require(test.Id != Guid.Empty && test.DisplayName is { Length: > 0 and <= 4096 },
                    "WitnessMissing");
                var identity = test.FullyQualifiedName + "(testCaseSha256: \""
                    + RuntimeSafety.Hash(new UTF8Encoding(false, true).GetBytes(
                        test.Id.ToString("D") + "\n" + test.DisplayName)) + "\")";
                RuntimeSafety.Require(cases.TryAdd(identity, new(identity, test.FullyQualifiedName)),
                    "EvidenceIncomplete");
            }
        }
        catch (Exception error) { Diagnostic = RuntimeResultRecorder.SafeCode(error); }
    }

    public void HandleDiscoveryComplete(long totalTests, IEnumerable<TestCase>? lastChunk, bool isAborted)
    {
        if (lastChunk is not null) { HandleDiscoveredTests(lastChunk); }
        if (Diagnostic == ConformanceDiagnosticCode.None)
        {
            try
            {
                RuntimeSafety.Require(!completed && !isAborted && totalTests == observed, "EvidenceIncomplete");
                RuntimeSafety.Require(methods.SetEquals(cases.Values.Select(entry => entry.FullyQualifiedName)),
                    "WitnessMissing");
                RuntimeSafety.Require(RuntimeSafety.FileHash(assembly) == assemblySha256, "InputChanged");
            }
            catch (Exception error) { Diagnostic = RuntimeResultRecorder.SafeCode(error); }
        }
        completed = true;
    }

    public void HandleLogMessage(TestMessageLevel level, string? message)
    {
        if (Diagnostic != ConformanceDiagnosticCode.None) { return; }
        if (message is not { Length: > 0 and <= 4096 })
        { Diagnostic = ConformanceDiagnosticCode.OutputLimitExceeded; return; }
        if (level == TestMessageLevel.Informational)
        {
            if (RuntimeSafety.AdapterBanner(message)) { return; }
            var body = RuntimeSafety.AdapterMessageBody(message);
            if (body is not null && RuntimeSafety.AdapterBanner(body)) { return; }
            if (body is not null && new[] { "Discovering:", "Discovered:" }.Any(prefix =>
                    body.StartsWith(prefix, StringComparison.Ordinal)
                    && body[prefix.Length..].Trim() == Path.GetFileNameWithoutExtension(assembly)))
            { return; }
        }
        Diagnostic = ConformanceDiagnosticCode.UnknownDiagnostic;
    }

    // The translation layer also supplies duplicate raw protocol messages; only typed events are admitted.
    public void HandleRawMessage(string rawMessage) { }
}
