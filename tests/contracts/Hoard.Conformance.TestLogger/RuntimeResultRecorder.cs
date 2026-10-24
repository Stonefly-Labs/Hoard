using System.Collections.Immutable;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Testing.Conformance.Catalog;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;

namespace Hoard.Conformance.TestLogger;

/// <summary>Projects actual VSTest results; callers must independently evaluate the complete run.</summary>
/// <remarks>
/// Witness times use absolute Stopwatch.GetTimestamp()/Stopwatch.Frequency milliseconds,
/// matching Linux CLOCK_MONOTONIC and the controller's time.monotonic()*1000 basis.
/// End is result-observation time; start subtracts the adapter's measured test duration.
/// VSTest logger events do not expose individual monotonic test-start notifications.
/// </remarks>
public sealed class RuntimeResultRecorder : IDisposable
{
    private readonly string root;
    private readonly Guid attemptId;
    private readonly string manifestDigest;
    private readonly string ownerDigest;
    private readonly RuntimeInput input;
    private readonly Dictionary<string, RuntimeExpectedTest> expected;
    private readonly Dictionary<string, RuntimeFile> assemblies;
    private readonly Dictionary<string, RuntimeFile> packages;
    private readonly HashSet<string> selectedMethods;
    private readonly HashSet<string> seen = new(StringComparer.Ordinal);
    private readonly HashSet<Guid> seenSessions = [];
    private readonly Dictionary<Guid, RuntimeOriginOutput.ComponentIdentity> seenInstances = [];
    private readonly HashSet<string> unmatchedMessages = new(StringComparer.Ordinal);
    private readonly HashSet<string> failureLines = new(StringComparer.Ordinal);
    private readonly FileStream witnesses;
    private readonly IncrementalHash recordsHash;
    private readonly string output;
    private readonly object gate = new();
    private long bytesWritten;
    private int observed;
    private int discovered;
    private bool completed;
    private ConformanceDiagnosticCode diagnostic;

    public RuntimeResultRecorder(string root, Guid attemptId, string manifestDigest, string ownerDigest)
    {
        RuntimeSafety.Require(attemptId != Guid.Empty, "OwnershipInvalid");
        this.root = Path.GetFullPath(root);
        this.attemptId = attemptId;
        this.manifestDigest = manifestDigest;
        this.ownerDigest = ownerDigest;
        RuntimeSafety.PrivateRoot(this.root);
        RuntimeSafety.Require(Directory.Exists(this.root), "OwnershipInvalid");
        var owner = RuntimeSafety.Read<RuntimeOwner>(RuntimeSafety.OwnedPath(this.root, "runtime-owner.json"), ownerDigest);
        input = RuntimeSafety.Read<RuntimeInput>(ManifestPath, manifestDigest);
        Validate(owner);
        expected = input.Expected.ToDictionary(entry => entry.TestIdentity, StringComparer.Ordinal);
        selectedMethods = input.Expected.Select(entry => entry.FullyQualifiedName).ToHashSet(StringComparer.Ordinal);
        assemblies = input.Assemblies.ToDictionary(entry => entry.Id, StringComparer.Ordinal);
        packages = input.Packages.ToDictionary(entry => entry.Id, StringComparer.Ordinal);
        VerifyInputs();
        output = RuntimeSafety.OwnedPath(this.root, $"{(IsDiscovery ? "discovery" : "runtime")}-{attemptId:D}");
        RuntimeSafety.Require(!Directory.Exists(output) && !File.Exists(output), "OwnershipInvalid");
        // The CreateNew claim is retained, including after failure; an attempt can never be replayed.
        using (new FileStream(RuntimeSafety.OwnedPath(this.root, $"runtime-{attemptId:D}.claim"),
            FileMode.CreateNew, FileAccess.Write, FileShare.None)) { }
        Directory.CreateDirectory(output);
        witnesses = new FileStream(RuntimeSafety.OwnedPath(output, IsDiscovery ? "discovered.jsonl" : "witnesses.jsonl"),
            FileMode.CreateNew, FileAccess.Write, FileShare.Read);
        recordsHash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    }

    private string ManifestPath => RuntimeSafety.OwnedPath(root, $"runtime-input-{attemptId:D}.json");
    public ConformanceDiagnosticCode Diagnostic => diagnostic;
    public int ObservedCount => observed;
    public bool IsDiscovery => input.Purpose == "discovery";

    private void Validate(RuntimeOwner owner)
    {
        RuntimeSafety.Require(owner.SchemaVersion == 1 && input.SchemaVersion == 1
            && input.Purpose is "execution" or "discovery"
            && owner.RunId != Guid.Empty && owner.InvocationGroupId != Guid.Empty
            && owner.RunId == input.RunId && owner.InvocationGroupId == input.InvocationGroupId
            && input.AttemptId == attemptId && input.AttemptSequence is >= 1 and <= 3, "OwnershipInvalid");
        RuntimeSafety.Id(owner.RootId);
        RuntimeSafety.Require(owner.RootPathSha256 == RuntimeSafety.RootHash(root), "OwnershipInvalid");
        RuntimeSafety.Digest(input.InputSha256);
        RuntimeSafety.OwnedPath(root, input.RunInputsPath);
        RuntimeSafety.Require(input.Assemblies is { Length: > 0 and <= 128 }
            && input.Packages is { Length: > 0 and <= 128 }
            && input.Expected is { Length: > 0 and <= RuntimeSafety.MaxTests });
        var fileIds = new HashSet<string>(StringComparer.Ordinal);
        var paths = new HashSet<string>(StringComparer.Ordinal) { input.RunInputsPath };
        foreach (var file in input.Assemblies.Concat(input.Packages))
        {
            RuntimeSafety.Require(file is not null);
            RuntimeSafety.Id(file.Id);
            RuntimeSafety.Digest(file.Sha256);
            RuntimeSafety.Require(fileIds.Add(file.Id) && paths.Add(file.Path));
            RuntimeSafety.OwnedPath(root, file.Path);
        }
        var identities = new HashSet<string>(StringComparer.Ordinal);
        foreach (var entry in input.Expected)
        {
            RuntimeSafety.Require(entry is not null);
            RuntimeSafety.Identity(entry.TestIdentity);
            RuntimeSafety.Identity(entry.FullyQualifiedName);
            RuntimeSafety.IdentityPair(entry.TestIdentity, entry.FullyQualifiedName);
            RuntimeSafety.Id(entry.BindingId);
            RuntimeSafety.Id(entry.MatrixId);
            RuntimeSafety.Id(entry.CaseId);
            RuntimeSafety.Require(identities.Add(entry.TestIdentity)
                && input.Assemblies.Any(file => file.Id == entry.AssemblyId)
                && input.Packages.Any(file => file.Id == entry.PackageId));
            RuntimeSafety.Require(entry.AssertionSymbol is null
                || (entry.AssertionSymbol.Length <= 256
                    && entry.AssertionSymbol.StartsWith("Hoard.Testing.Conformance.", StringComparison.Ordinal)
                    && entry.AssertionSymbol.All(c => char.IsAsciiLetterOrDigit(c) || c is '.' or '_')));
        }
    }

    private void VerifyProvenance()
    {
        RuntimeSafety.PrivateRoot(root);
        _ = RuntimeSafety.Read<RuntimeOwner>(RuntimeSafety.OwnedPath(root, "runtime-owner.json"), ownerDigest);
        _ = RuntimeSafety.Read<RuntimeInput>(ManifestPath, manifestDigest);
        RuntimeSafety.VerifyRunInputs(RuntimeSafety.OwnedPath(root, input.RunInputsPath),
            input.InputSha256, input.RunId, input.InvocationGroupId);
        RuntimeSafety.CheckLinks(output ?? root);
    }

    private void VerifyInputs()
    {
        RuntimeSafety.VerifyRunInputs(RuntimeSafety.OwnedPath(root, input.RunInputsPath),
            input.InputSha256, input.RunId, input.InvocationGroupId);
        long total = 0;
        foreach (var file in input.Assemblies.Concat(input.Packages))
        {
            var path = RuntimeSafety.OwnedPath(root, file.Path);
            total += new FileInfo(path).Length;
            RuntimeSafety.Require(total <= 512 * 1024 * 1024, "OutputLimitExceeded");
            RuntimeSafety.Require(RuntimeSafety.FileHash(path) == file.Sha256,
                "InputChanged");
        }
    }

    private (RuntimeExpectedTest Entry, RuntimeFile Assembly) AdmitTestCase(TestCase test, string identity)
    {
        RuntimeSafety.Require(++observed <= RuntimeSafety.MaxTests, "OutputLimitExceeded");
        VerifyProvenance();
        RuntimeSafety.Require(identity is { Length: > 0 and <= 1024 }
            && expected.ContainsKey(identity), "WitnessMissing");
        var entry = expected[identity];
        RuntimeSafety.Require(seen.Add(identity), "EvidenceIncomplete");
        RuntimeSafety.Require(test.FullyQualifiedName == entry.FullyQualifiedName, "WitnessMissing");
        var assembly = assemblies[entry.AssemblyId];
        var path = RuntimeSafety.OwnedPath(root, assembly.Path);
        RuntimeSafety.Require(test.Source is { Length: > 0 and <= 4096 }
            && Path.GetFullPath(test.Source) == path, "ProofMismatch");
        RuntimeSafety.Require(RuntimeSafety.FileHash(path) == assembly.Sha256, "InputChanged");
        return (entry, assembly);
    }

    public void ObserveDiscovery(TestCase test)
    {
        lock (gate)
        {
            if (completed || diagnostic != ConformanceDiagnosticCode.None) { return; }
            try
            {
                RuntimeSafety.Require(IsDiscovery && test is not null, "ProofMismatch");
                RuntimeSafety.Require(++discovered <= RuntimeSafety.MaxTests, "OutputLimitExceeded");
                // Discovery can enumerate other methods in the same assembly; select exact methods,
                // then require every parameter identity of those methods to match independently.
                if (!selectedMethods.Contains(test.FullyQualifiedName)) { return; }
                var (entry, assembly) = AdmitTestCase(test, test.DisplayName);
                var bytes = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    schemaVersion = 1,
                    runId = input.RunId,
                    invocationGroupId = input.InvocationGroupId,
                    attemptId,
                    attemptSequence = input.AttemptSequence,
                    inputSha256 = input.InputSha256,
                    manifestSha256 = manifestDigest,
                    ownerSha256 = ownerDigest,
                    testIdentity = entry.TestIdentity,
                    fullyQualifiedName = entry.FullyQualifiedName,
                    assemblySha256 = assembly.Sha256,
                    discoveredMs = Stopwatch.GetTimestamp() * 1000.0 / Stopwatch.Frequency
                }, RuntimeSafety.Json);
                Reserve(bytes.Length + 1);
                WriteRecord(bytes);
            }
            catch (Exception error) { Fail(SafeCode(error)); }
        }
    }

    public void Observe(TestResult result)
    {
        lock (gate)
        {
            if (completed || diagnostic != ConformanceDiagnosticCode.None) { return; }
            try
            {
                RuntimeSafety.Require(!IsDiscovery && result is not null, "ProofMismatch");
                var identity = result.DisplayName ?? result.TestCase.DisplayName;
                var (entry, assembly) = AdmitTestCase(result.TestCase, identity);
                var executionId = Guid.NewGuid();
                var ended = TimeSpan.FromMilliseconds(Stopwatch.GetTimestamp() * 1000.0 / Stopwatch.Frequency);
                RuntimeSafety.Require(result.Duration >= TimeSpan.Zero
                    && result.Duration <= TimeSpan.FromHours(8) && result.Duration <= ended);
                var started = ended - result.Duration;
                var kind = FailureKind(result, entry);
                if (result.Outcome == TestOutcome.Failed) { CorrelateFailureMessages(result); }
                RuntimeSafety.Require(diagnostic == ConformanceDiagnosticCode.None, diagnostic.ToString());
                var (sessionOrigins, unknownOutput, instances) =
                    RuntimeOriginOutput.Read(result, input, entry, seenSessions, seenInstances);
                if (unknownOutput || (result.Outcome == TestOutcome.Passed
                    && (!string.IsNullOrEmpty(result.ErrorMessage) || !string.IsNullOrEmpty(result.ErrorStackTrace))))
                { unknownDiagnostic = true; }
                var status = result.Outcome switch
                {
                    TestOutcome.Passed => ConformanceWitnessStatus.Passed,
                    TestOutcome.Failed => ConformanceWitnessStatus.Failed,
                    _ => ConformanceWitnessStatus.Incomplete
                };
                var proof = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    schemaVersion = 1,
                    executionId,
                    runId = input.RunId,
                    invocationGroupId = input.InvocationGroupId,
                    attemptId,
                    attemptSequence = input.AttemptSequence,
                    testIdentity = entry.TestIdentity,
                    bindingId = entry.BindingId,
                    matrixId = entry.MatrixId,
                    caseId = entry.CaseId,
                    inputSha256 = input.InputSha256,
                    manifestSha256 = manifestDigest,
                    ownerSha256 = ownerDigest,
                    assemblySha256 = assembly.Sha256,
                    packageSha256 = packages[entry.PackageId].Sha256,
                    clock = "system-monotonic-ms",
                    durationMs = result.Duration.TotalMilliseconds,
                    failureKind = kind,
                    assertionSymbol = kind == "Assertion" ? entry.AssertionSymbol : null,
                    status = status.ToString(),
                    sessionOrigins
                }, RuntimeSafety.Json);
                RuntimeSafety.Require(proof.Length <= 64 * 1024, "OutputLimitExceeded");
                var expectedCase = new ConformanceExpectedCase("harness", entry.BindingId, entry.MatrixId,
                    "runtime", ImmutableArray.Create(entry.TestIdentity), [], null);
                var witness = new ConformanceRuntimeWitness(executionId, input.RunId, input.InvocationGroupId,
                    expectedCase, entry.TestIdentity, packages[entry.PackageId].Sha256, assembly.Sha256,
                    input.InputSha256, started, ended, status, RuntimeSafety.Hash(proof));
                var line = JsonSerializer.SerializeToUtf8Bytes(witness, RuntimeSafety.Json);
                Reserve(proof.Length + line.Length + 1);
                WriteNew($"proof-{executionId:D}.json", proof);
                WriteRecord(line);
                foreach (var origin in sessionOrigins)
                { seenSessions.Add(origin.GetProperty("sessionId").GetGuid()); }
                foreach (var (id, componentIdentity) in instances) { seenInstances.TryAdd(id, componentIdentity); }
                if (status == ConformanceWitnessStatus.Incomplete) { incomplete = true; }
                else if (status == ConformanceWitnessStatus.Failed)
                {
                    // Retain subsequent actual results; an assertion failure is not an ingestion failure.
                    // The completion record records the failure independently from inventory completeness.
                    failed = true;
                    if (kind != "Assertion") { unknownDiagnostic = true; }
                }
            }
            catch (Exception error) { Fail(SafeCode(error)); }
        }
    }

    private bool failed;
    private bool incomplete;
    private bool unknownDiagnostic;

    public void ObserveMessage(string message)
    {
        lock (gate)
        {
            if (completed || diagnostic != ConformanceDiagnosticCode.None) { return; }
            if (message is not { Length: > 0 and <= 4096 }) { Fail(ConformanceDiagnosticCode.OutputLimitExceeded); return; }
            if (RuntimeSafety.AdapterBanner(message)) { return; }
            var body = RuntimeSafety.AdapterMessageBody(message);
            if (body is not null)
            {
                if (RuntimeSafety.AdapterBanner(body)) { return; }
                foreach (var prefix in new[] { "Discovering:", "Discovered:", "Starting:", "Finished:" })
                {
                    if (body.StartsWith(prefix, StringComparison.Ordinal)
                        && input.Assemblies.Any(file => body[prefix.Length..].Trim() == Path.GetFileNameWithoutExtension(file.Path)))
                    { return; }
                }
                foreach (var suffix in new[] { " [FAIL]", " [SKIP]" })
                {
                    if (body.EndsWith(suffix, StringComparison.Ordinal)
                        && expected.ContainsKey(body[..^suffix.Length]))
                    { return; }
                }
            }
            // Only exact hashes of the actual failed result's lines can discharge adapter-rendered
            // failures. No raw line is retained while waiting for TestResult, in either event order.
            var fingerprint = MessageHash(body ?? message);
            if (!failureLines.Contains(fingerprint)) { unmatchedMessages.Add(fingerprint); }
            BoundMessageHashes();
        }
    }

    private static string MessageHash(string line) => RuntimeSafety.Hash(Encoding.UTF8.GetBytes(line.Trim()));

    private void BoundMessageHashes()
    {
        if (unmatchedMessages.Count + failureLines.Count > 4096)
        { Fail(ConformanceDiagnosticCode.OutputLimitExceeded); }
    }

    private void CorrelateFailureMessages(TestResult result)
    {
        if (result.ErrorMessage is not { Length: <= 16_384 }
            || result.ErrorStackTrace is not { Length: <= 65_536 }) { return; }
        AddFailureLine("Stack Trace:");
        foreach (var text in new[] { result.ErrorMessage, result.ErrorStackTrace })
        {
            foreach (var span in text.AsSpan().EnumerateLines())
            {
                if (span.Length is 0 or > 4096) { continue; }
                var line = span.Trim().ToString();
                AddFailureLine(line);
                var source = line.LastIndexOf(" in ", StringComparison.Ordinal);
                var number = line.LastIndexOf(":line ", StringComparison.Ordinal);
                if (source > 0 && number > source
                    && int.TryParse(line.AsSpan(number + 6), out var lineNumber) && lineNumber >= 0)
                {
                    AddFailureLine($"{line[(source + 4)..number]}({lineNumber},0): {line[..source]}");
                }
            }
        }
    }

    private void AddFailureLine(string line)
    {
        if (diagnostic != ConformanceDiagnosticCode.None) { return; }
        var fingerprint = MessageHash(line);
        unmatchedMessages.Remove(fingerprint);
        failureLines.Add(fingerprint);
        BoundMessageHashes();
    }

    private static string FailureKind(TestResult result, RuntimeExpectedTest entry)
    {
        if (result.Outcome == TestOutcome.Passed) { return "None"; }
        if (result.Outcome != TestOutcome.Failed) { return "SkippedOrUnknown"; }
        // Raw adapter text is inspected only as bounded transient input, and never copied to evidence.
        if (entry.AssertionSymbol is null || result.ErrorMessage is not { Length: > 0 and <= 16_384 }
            || result.ErrorStackTrace is not { Length: > 0 and <= 65_536 })
        { return "Unknown"; }
        var assertion = new[] { "Assert.True() Failure", "Assert.False() Failure", "Assert.Equal() Failure",
            "Assert.NotEqual() Failure", "Assert.Null() Failure", "Assert.NotNull() Failure",
            "Assert.Contains() Failure", "Assert.DoesNotContain() Failure", "Assert.Throws() Failure",
            "Assert.Fail() Failure" }.Any(prefix => result.ErrorMessage.StartsWith(prefix, StringComparison.Ordinal));
        var frame = "at " + entry.AssertionSymbol + "(";
        if (assertion)
        {
            foreach (var line in result.ErrorStackTrace.AsSpan().EnumerateLines())
            {
                if (line.TrimStart().StartsWith(frame, StringComparison.Ordinal)) { return "Assertion"; }
            }
        }
        return "Unknown";
    }

    public void Fail(ConformanceDiagnosticCode code)
    {
        lock (gate)
        {
            if (diagnostic == ConformanceDiagnosticCode.None)
            { diagnostic = Enum.IsDefined(code) && code != ConformanceDiagnosticCode.None ? code : ConformanceDiagnosticCode.UnknownDiagnostic; }
        }
    }

    public void Complete(bool aborted = false)
    {
        lock (gate)
        {
            if (completed) { return; }
            try
            {
                VerifyProvenance();
                VerifyInputs();
                if (aborted || incomplete || seen.Count != expected.Count) { Fail(ConformanceDiagnosticCode.EvidenceIncomplete); }
                if (unknownDiagnostic || unmatchedMessages.Count > 0) { Fail(ConformanceDiagnosticCode.UnknownDiagnostic); }
                if (failed && diagnostic == ConformanceDiagnosticCode.None) { Fail(ConformanceDiagnosticCode.AssertionFailed); }
                var bytes = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    schemaVersion = 1,
                    runId = input.RunId,
                    invocationGroupId = input.InvocationGroupId,
                    attemptId,
                    attemptSequence = input.AttemptSequence,
                    purpose = input.Purpose,
                    manifestSha256 = manifestDigest,
                    inputSha256 = input.InputSha256,
                    recordsSha256 = Convert.ToHexStringLower(recordsHash.GetCurrentHash()),
                    diagnosticCode = diagnostic.ToString(),
                    observedCount = observed,
                    expectedCount = expected.Count,
                    complete = !aborted && seen.Count == expected.Count && diagnostic is
                        ConformanceDiagnosticCode.None or ConformanceDiagnosticCode.AssertionFailed
                }, RuntimeSafety.Json);
                Reserve(bytes.Length);
                WriteNew("completion.json", bytes);
            }
            catch (Exception error) { Fail(SafeCode(error)); }
            finally { completed = true; witnesses.Dispose(); recordsHash.Dispose(); }
        }
    }

    private void Reserve(int count)
    {
        RuntimeSafety.Require(bytesWritten + count <= RuntimeSafety.MaxOutputBytes, "OutputLimitExceeded");
        bytesWritten += count;
    }

    private void WriteRecord(byte[] bytes)
    {
        witnesses.Write(bytes);
        witnesses.WriteByte((byte)'\n');
        recordsHash.AppendData(bytes);
        recordsHash.AppendData("\n"u8);
        witnesses.Flush();
    }

    private void WriteNew(string name, byte[] bytes)
    {
        using var file = new FileStream(RuntimeSafety.OwnedPath(output, name),
            FileMode.CreateNew, FileAccess.Write, FileShare.Read);
        file.Write(bytes);
        file.Flush(true);
    }

    internal static ConformanceDiagnosticCode SafeCode(Exception error) =>
        error is InvalidDataException && Enum.TryParse<ConformanceDiagnosticCode>(error.Message, out var code)
            && Enum.IsDefined(code) ? code : ConformanceDiagnosticCode.EvidenceSchemaInvalid;

    public void Dispose() => Complete(true);
}
