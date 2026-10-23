using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;

namespace Hoard.Conformance.Tests;

public sealed class RuntimeLoggerTests
{
    [Fact]
    public void Discovery_preserves_exact_selected_parameters_without_fabricating_execution_witnesses()
    {
        using var owned = new OwnedInput(2, purpose: "discovery");
        using (var recorder = owned.Open())
        {
            var unrelated = owned.Result(0).TestCase;
            unrelated.FullyQualifiedName = "Hoard.Unselected.Check";
            unrelated.DisplayName = "private-canary";
            recorder.ObserveDiscovery(unrelated);
            recorder.ObserveDiscovery(owned.Result(0).TestCase);
            recorder.ObserveDiscovery(owned.Result(1).TestCase);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
            Assert.Equal(2, recorder.ObservedCount);
        }
        var lines = File.ReadAllLines(Path.Combine(owned.Output, "discovered.jsonl"));
        Assert.Equal(2, lines.Length);
        for (var index = 0; index < lines.Length; index++)
        {
            using var document = JsonDocument.Parse(lines[index]);
            Assert.Equal(owned.Input.Expected[index].TestIdentity, document.RootElement.GetProperty("testIdentity").GetString());
            Assert.False(document.RootElement.TryGetProperty("executionId", out _));
        }
        Assert.False(File.Exists(Path.Combine(owned.Output, "witnesses.jsonl")));
        Assert.Empty(Directory.GetFiles(owned.Output, "proof-*.json"));
        using var completion = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(owned.Output, "completion.json")));
        Assert.Equal("discovery", completion.RootElement.GetProperty("purpose").GetString());
        Assert.Equal(Hash(File.ReadAllBytes(Path.Combine(owned.Output, "discovered.jsonl"))),
            completion.RootElement.GetProperty("recordsSha256").GetString());
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("parameter", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("source", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("duplicate", ConformanceDiagnosticCode.EvidenceIncomplete)]
    public void Discovery_rejects_selected_parameter_source_or_duplicate_changes_without_erasing_prior_records(
        string mutation, ConformanceDiagnosticCode code)
    {
        using var owned = new OwnedInput(2, purpose: "discovery");
        using var recorder = owned.Open();
        recorder.ObserveDiscovery(owned.Result(0).TestCase);
        var before = File.ReadAllBytes(Path.Combine(owned.Output, "discovered.jsonl"));
        var test = owned.Result(mutation == "duplicate" ? 0 : 1).TestCase;
        if (mutation == "parameter") { test.DisplayName = "Hoard.Frozen.Check(value: 99)"; }
        if (mutation == "source") { test.Source = Path.Combine(owned.Root, "foreign.dll"); }
        recorder.ObserveDiscovery(test);
        recorder.Complete();
        Assert.Equal(code, recorder.Diagnostic);
        Assert.Equal(before, File.ReadAllBytes(Path.Combine(owned.Output, "discovered.jsonl")));
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData(ConformanceCategory.Metadata)]
    [InlineData(ConformanceCategory.Artifacts)]
    public void Finite_enum_parameters_preserve_exact_parent_expected_identity(ConformanceCategory category)
    {
        using var owned = new OwnedInput();
        var identity = $"Hoard.Frozen.Check(category: {category})";
        owned.Input.Expected[0] = owned.Input.Expected[0] with { TestIdentity = identity };
        owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json));
        using (var recorder = owned.Open())
        {
            recorder.Observe(owned.Result(0));
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var witness = JsonDocument.Parse(File.ReadAllText(Path.Combine(owned.Output, "witnesses.jsonl")));
        Assert.Equal(identity, witness.RootElement.GetProperty("testIdentity").GetString());
    }

    [Theory]
    [InlineData("[1.2.0,2.0.0)")]
    [InlineData("(2.0.0,1.0.0]")]
    [InlineData("[1.2.3]")]
    public void Finite_version_ranges_preserve_exact_parameter_identity(string range)
    {
        using var owned = new OwnedInput();
        var identity = $"Hoard.Frozen.Check(range: \"{range}\")";
        owned.Input.Expected[0] = owned.Input.Expected[0] with { TestIdentity = identity };
        owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json));
        using (var recorder = owned.Open())
        {
            recorder.Observe(owned.Result(0));
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var witness = JsonDocument.Parse(File.ReadAllText(Path.Combine(owned.Output, "witnesses.jsonl")));
        Assert.Equal(identity, witness.RootElement.GetProperty("testIdentity").GetString());
    }

    [Fact]
    public void Actual_results_preserve_each_parameter_identity_and_append_only_attempts()
    {
        using var owned = new OwnedInput(2);
        var before = System.Diagnostics.Stopwatch.GetTimestamp() * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
        using (var recorder = owned.Open())
        {
            recorder.Observe(owned.Result(0));
            recorder.Observe(owned.Result(1));
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        var lines = File.ReadAllLines(Path.Combine(owned.Output, "witnesses.jsonl"));
        Assert.Equal(2, lines.Length);
        var executions = new HashSet<Guid>();
        for (var index = 0; index < lines.Length; index++)
        {
            using var witness = JsonDocument.Parse(lines[index]);
            var entry = witness.RootElement;
            Assert.Equal(owned.Input.Expected[index].TestIdentity, entry.GetProperty("testIdentity").GetString());
            Assert.Equal(owned.Input.RunId, entry.GetProperty("runId").GetGuid());
            Assert.Equal("memory", entry.GetProperty("bindingId").GetString());
            Assert.Equal("matrix", entry.GetProperty("matrixId").GetString());
            Assert.True(executions.Add(entry.GetProperty("executionId").GetGuid()));
            Assert.True(entry.GetProperty("endedMs").GetDouble() >= before);
            var proof = File.ReadAllBytes(Path.Combine(owned.Output, $"proof-{entry.GetProperty("executionId").GetGuid():D}.json"));
            Assert.Equal(Hash(proof), entry.GetProperty("proofSha256").GetString());
        }
        Assert.Throws<InvalidDataException>(() => owned.Open());
        Assert.Equal(lines, File.ReadAllLines(Path.Combine(owned.Output, "witnesses.jsonl")));
    }

    [Fact]
    public void Assertion_proof_requires_both_frozen_symbol_and_xunit_prefix_and_never_retains_raw_text()
    {
        using var owned = new OwnedInput(2);
        using var recorder = owned.Open();
        var assertion = owned.Result(0, TestOutcome.Failed);
        assertion.ErrorMessage = "Assert.True() Failure\ncanary-secret-provider-text";
        assertion.ErrorStackTrace = "   at Hoard.Testing.Conformance.FrozenAssertion.Check()\n/private/canary-path";
        recorder.Observe(assertion);
        var unknown = owned.Result(1, TestOutcome.Failed);
        unknown.ErrorMessage = "canary-secret-provider-text";
        unknown.ErrorStackTrace = "   at Hoard.Testing.Conformance.FrozenAssertion.Check()";
        unknown.Messages.Add(new TestResultMessage(TestResultMessage.StandardOutCategory, "canary-stdout"));
        recorder.Observe(unknown);
        recorder.Complete();
        Assert.Equal(ConformanceDiagnosticCode.UnknownDiagnostic, recorder.Diagnostic);
        var proofs = Directory.GetFiles(owned.Output, "proof-*.json")
            .Select(path => JsonDocument.Parse(File.ReadAllBytes(path))).ToArray();
        try
        {
            Assert.Contains(proofs, proof => proof.RootElement.GetProperty("failureKind").GetString() == "Assertion");
            Assert.Contains(proofs, proof => proof.RootElement.GetProperty("failureKind").GetString() == "Unknown"
                && proof.RootElement.GetProperty("assertionSymbol").ValueKind == JsonValueKind.Null);
        }
        finally { foreach (var proof in proofs) { proof.Dispose(); } }
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("duplicate", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("parameter", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("qualified-name", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("source", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("skipped", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("stale", ConformanceDiagnosticCode.InputChanged)]
    [InlineData("stale-input", ConformanceDiagnosticCode.InputChanged)]
    public void Missing_mutated_duplicate_and_skipped_observations_cannot_complete(string mutation,
        ConformanceDiagnosticCode expectedCode)
    {
        using var owned = new OwnedInput();
        using var recorder = owned.Open();
        var result = owned.Result(0);
        switch (mutation)
        {
            case "duplicate": recorder.Observe(result); break;
            case "parameter": result.DisplayName = "canary-unknown(value: 99)"; break;
            case "qualified-name": result.TestCase.FullyQualifiedName = "canary-unknown"; break;
            case "source": result.TestCase.Source = Path.Combine(owned.Root, "foreign-canary.dll"); break;
            case "skipped": result.Outcome = TestOutcome.Skipped; break;
            case "stale": File.AppendAllText(owned.AssemblyPath, "changed"); break;
            case "stale-input": File.AppendAllText(Path.Combine(owned.Root, "run-inputs.json"), "changed"); break;
        }
        if (mutation != "missing") { recorder.Observe(result); }
        recorder.Complete();
        Assert.Equal(expectedCode, recorder.Diagnostic);
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("owner")]
    [InlineData("manifest")]
    [InlineData("duplicate-key")]
    [InlineData("unknown-field")]
    [InlineData("purpose-omitted")]
    [InlineData("purpose-unknown")]
    [InlineData("input-hash")]
    [InlineData("symlink")]
    [InlineData("parameter-omitted")]
    [InlineData("private-identity")]
    [InlineData("enum-overflow")]
    [InlineData("enum-text")]
    [InlineData("enum-path")]
    [InlineData("moved-root")]
    public void Foreign_or_malformed_inputs_are_rejected_before_output_creation(string mutation)
    {
        using var owned = new OwnedInput();
        switch (mutation)
        {
            case "owner": File.AppendAllText(owned.OwnerPath, " "); break;
            case "manifest": File.AppendAllText(owned.ManifestPath, " "); break;
            case "input-hash": File.AppendAllText(owned.AssemblyPath, "changed"); break;
            case "duplicate-key":
                owned.RewriteManifest(File.ReadAllText(owned.ManifestPath).Replace("\"schemaVersion\":1",
                    "\"schemaVersion\":1,\"schemaVersion\":1", StringComparison.Ordinal)); break;
            case "unknown-field":
                owned.RewriteManifest(File.ReadAllText(owned.ManifestPath).Replace("\"schemaVersion\":1",
                    "\"schemaVersion\":1,\"unknown\":true", StringComparison.Ordinal)); break;
            case "purpose-omitted":
                owned.RewriteManifest(File.ReadAllText(owned.ManifestPath).Replace(
                    ",\"purpose\":\"execution\"", "", StringComparison.Ordinal)); break;
            case "purpose-unknown":
                owned.RewriteManifest(JsonSerializer.Serialize(owned.Input with { Purpose = "unknown" }, Json)); break;
            case "symlink":
                File.Move(owned.AssemblyPath, owned.AssemblyPath + ".target");
                File.CreateSymbolicLink(owned.AssemblyPath, owned.AssemblyPath + ".target"); break;
            case "parameter-omitted":
                owned.Input.Expected[0] = owned.Input.Expected[0] with { TestIdentity = "" };
                owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json)); break;
            case "private-identity":
                owned.Input.Expected[0] = owned.Input.Expected[0] with { TestIdentity = "Hoard.Frozen.Check(value: \"/private/canary\")" };
                owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json)); break;
            case "enum-overflow":
            case "enum-text":
            case "enum-path":
                var parameter = mutation == "enum-overflow" ? new string('A', 129)
                    : mutation == "enum-text" ? "Metadata Artifacts" : "../Metadata";
                owned.Input.Expected[0] = owned.Input.Expected[0] with
                { TestIdentity = $"Hoard.Frozen.Check(category: {parameter})" };
                owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json)); break;
            case "moved-root":
                var owner = JsonSerializer.Deserialize<RuntimeOwner>(File.ReadAllBytes(owned.OwnerPath), Json)!;
                owned.RewriteOwner(owner with { RootPathSha256 = new string('b', 64) }); break;
        }
        Assert.ThrowsAny<Exception>(() => owned.Open());
        Assert.False(Directory.Exists(owned.Output));
    }

    [Fact]
    public void Input_mutation_after_actual_results_invalidates_completion_without_rewriting_a_witness()
    {
        using var owned = new OwnedInput();
        using var recorder = owned.Open();
        recorder.Observe(owned.Result(0));
        var before = File.ReadAllBytes(Path.Combine(owned.Output, "witnesses.jsonl"));
        File.AppendAllText(owned.ManifestPath, " ");
        recorder.Complete();
        Assert.Equal(ConformanceDiagnosticCode.InputChanged, recorder.Diagnostic);
        Assert.False(File.Exists(Path.Combine(owned.Output, "completion.json")));
        Assert.Equal(before, File.ReadAllBytes(Path.Combine(owned.Output, "witnesses.jsonl")));
    }

    [Fact]
    public void Unknown_run_messages_block_an_otherwise_passing_result_without_retaining_canaries()
    {
        using var owned = new OwnedInput();
        using var recorder = owned.Open();
        recorder.ObserveMessage("canary-unrecognized-run-message");
        recorder.Observe(owned.Result(0));
        recorder.Complete();
        Assert.Equal(ConformanceDiagnosticCode.UnknownDiagnostic, recorder.Diagnostic);
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData(false, ConformanceDiagnosticCode.AssertionFailed)]
    [InlineData(true, ConformanceDiagnosticCode.UnknownDiagnostic)]
    public void Adapter_rendering_is_correlated_to_actual_failure_lines_not_trusted_as_an_assertion(
        bool extra, ConformanceDiagnosticCode expected)
    {
        using var owned = new OwnedInput();
        using var recorder = owned.Open();
        recorder.ObserveMessage("[xUnit.net 00:00:00.01]       Assert.True() Failure");
        recorder.ObserveMessage("[xUnit.net 00:00:00.01]       Stack Trace:");
        var result = owned.Result(0, TestOutcome.Failed);
        result.ErrorMessage = "Assert.True() Failure";
        result.ErrorStackTrace = "   at Hoard.Testing.Conformance.FrozenAssertion.Check()";
        recorder.Observe(result);
        recorder.ObserveMessage("[xUnit.net 00:00:00.01]       at Hoard.Testing.Conformance.FrozenAssertion.Check()");
        if (extra) { recorder.ObserveMessage("[xUnit.net 00:00:00.01]       canary-unrelated-setup-error"); }
        recorder.Complete();
        Assert.Equal(expected, recorder.Diagnostic);
        AssertSafe(owned.Output);
    }

    [Fact]
    public void Oversized_diagnostic_input_fails_closed_without_spooling_or_truncating_into_success()
    {
        using var owned = new OwnedInput();
        using var recorder = owned.Open();
        recorder.ObserveMessage(new string('x', 4097));
        recorder.Observe(owned.Result(0));
        recorder.Complete();
        Assert.Equal(ConformanceDiagnosticCode.OutputLimitExceeded, recorder.Diagnostic);
        Assert.Empty(File.ReadAllText(Path.Combine(owned.Output, "witnesses.jsonl")));
        AssertSafe(owned.Output);
    }

    private static void AssertSafe(string output)
    {
        foreach (var file in Directory.GetFiles(output))
        {
            Assert.DoesNotContain("canary", Path.GetFileName(file), StringComparison.Ordinal);
            var text = File.ReadAllText(file);
            Assert.DoesNotContain("canary", text, StringComparison.Ordinal);
            Assert.DoesNotContain("ErrorMessage", text, StringComparison.Ordinal);
            Assert.DoesNotContain("StackTrace", text, StringComparison.Ordinal);
        }
    }

    private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private sealed class OwnedInput : IDisposable
    {
        internal string Root { get; } = Path.GetFullPath(Path.Combine(".runtime-logger-tests", Guid.NewGuid().ToString("D")));
        internal RuntimeInput Input { get; }
        internal string AssemblyPath => Path.Combine(Root, "tests.dll");
        internal string OwnerPath => Path.Combine(Root, "runtime-owner.json");
        internal string ManifestPath => Path.Combine(Root, $"runtime-input-{Input.AttemptId:D}.json");
        internal string Output => Path.Combine(Root,
            $"{(Input.Purpose == "discovery" ? "discovery" : "runtime")}-{Input.AttemptId:D}");
        private string ownerHash;
        private string manifestHash;

        internal OwnedInput(int count = 1, string purpose = "execution")
        {
            Directory.CreateDirectory(Root);
            if (!OperatingSystem.IsWindows())
            {
                File.SetUnixFileMode(Root, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            }
            File.Copy(typeof(RuntimeLoggerTests).Assembly.Location, AssemblyPath);
            File.WriteAllText(Path.Combine(Root, "fixture.nupkg"), "unit-test-only-not-a-package-proof");
            var runId = Guid.NewGuid();
            var groupId = Guid.NewGuid();
            var owner = JsonSerializer.SerializeToUtf8Bytes(new RuntimeOwner(1, runId, groupId, "owned",
                Hash(Encoding.UTF8.GetBytes(Root))), Json);
            File.WriteAllBytes(OwnerPath, owner);
            ownerHash = Hash(owner);
            var runInputs = JsonSerializer.SerializeToUtf8Bytes(new
            { schemaVersion = 1, runId, invocationGroupId = groupId, mode = "diagnostic" });
            File.WriteAllBytes(Path.Combine(Root, "run-inputs.json"), runInputs);
            Input = new(1, runId, groupId, Guid.NewGuid(), 1, Hash(runInputs), "run-inputs.json",
                [new("tests", "tests.dll", Hash(File.ReadAllBytes(AssemblyPath)))],
                [new("fixture", "fixture.nupkg", Hash(File.ReadAllBytes(Path.Combine(Root, "fixture.nupkg"))))],
                Enumerable.Range(0, count).Select(index => new RuntimeExpectedTest(
                    $"Hoard.Frozen.Check(value: {index})", "Hoard.Frozen.Check", "tests", "fixture", "memory", "matrix",
                    "Hoard.Testing.Conformance.FrozenAssertion.Check")).ToArray(), purpose);
            var manifest = JsonSerializer.SerializeToUtf8Bytes(Input, Json);
            File.WriteAllBytes(ManifestPath, manifest);
            manifestHash = Hash(manifest);
        }

        internal void RewriteManifest(string text)
        {
            File.WriteAllText(ManifestPath, text);
            manifestHash = Hash(Encoding.UTF8.GetBytes(text));
        }

        internal void RewriteOwner(RuntimeOwner owner)
        {
            var bytes = JsonSerializer.SerializeToUtf8Bytes(owner, Json);
            File.WriteAllBytes(OwnerPath, bytes);
            ownerHash = Hash(bytes);
        }

        internal RuntimeResultRecorder Open() => new(Root, Input.AttemptId, manifestHash, ownerHash);
        internal TestResult Result(int index, TestOutcome outcome = TestOutcome.Passed) =>
            new(new TestCase(Input.Expected[index].FullyQualifiedName, new Uri("executor://xunit/VsTestRunner2/netcore/"), AssemblyPath)
            { DisplayName = Input.Expected[index].TestIdentity })
            {
                DisplayName = Input.Expected[index].TestIdentity,
                Outcome = outcome,
                Duration = TimeSpan.FromMilliseconds(1)
            };

        public void Dispose() => Directory.Delete(Root, true);
    }
}
