using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;

namespace Hoard.Conformance.Tests;

public sealed class RuntimeLoggerTests
{
    [Theory]
    [InlineData("admission-denied")]
    [InlineData("denial-stopped")]
    [InlineData("repair-admitted")]
    [InlineData("repair-stopped")]
    public void Admission_snapshots_preserve_bounded_failure_and_root_observations(string stage)
    {
        using var owned = new OwnedInput();
        var owner = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-owner", [("owner", new OriginalProbe())]);
        var counters = new Dictionary<string, int>(StringComparer.Ordinal)
        {
            ["ready"] = 0,
            ["admission"] = 0,
            ["phaseFailures"] = 1,
            ["fallbackRoots"] = 0,
            ["workers"] = 0,
            ["stopComplete"] = 0,
            ["rootDisposal"] = 6,
            ["unsafeActivities"] = 0
        };
        var lines = ConformanceOriginalObservationOutput.Render(owner).Concat(
            ConformanceCompositionObservationOutput.Render(owner, stage, counters));
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        var snapshot = Assert.Single(proof.RootElement.GetProperty("compositionObservations").EnumerateArray());
        Assert.Equal(stage, snapshot.GetProperty("stage").GetString());
        Assert.Equal(1, snapshot.GetProperty("counters").GetProperty("phaseFailures").GetInt32());
        Assert.Equal(6, snapshot.GetProperty("counters").GetProperty("rootDisposal").GetInt32());
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("caller-cancelled")]
    [InlineData("ownership-retained")]
    [InlineData("ownership-settled")]
    [InlineData("ownership-stopped")]
    [InlineData("initialization-denied")]
    public void Ownership_snapshots_preserve_bounded_callback_and_root_observations(string stage)
    {
        using var owned = new OwnedInput();
        var owner = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-owner", [("owner", new OriginalProbe())]);
        var counters = new Dictionary<string, int>(StringComparer.Ordinal)
        {
            ["callbackSettled"] = 0,
            ["workCompleted"] = 0,
            ["workFaulted"] = 0,
            ["ready"] = 0,
            ["admission"] = 0,
            ["unsafeActivities"] = 1,
            ["rootDisposal"] = 4,
            ["stopComplete"] = 0,
            ["initializations"] = 1,
            ["assessments"] = 0,
            ["workers"] = 0,
            ["stops"] = 0,
            ["disposals"] = 0
        };
        var lines = ConformanceOriginalObservationOutput.Render(owner).Concat(
            ConformanceCompositionObservationOutput.Render(owner, stage, counters));
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        var snapshot = Assert.Single(proof.RootElement.GetProperty("compositionObservations").EnumerateArray());
        Assert.Equal(stage, snapshot.GetProperty("stage").GetString());
        Assert.Equal(4, snapshot.GetProperty("counters").GetProperty("rootDisposal").GetInt32());
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("memory")]
    [InlineData("none")]
    public void Composition_snapshots_remain_bound_to_the_actual_owner_and_test(string binding)
    {
        using var owned = new OwnedInput(binding: binding);
        var owner = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, binding,
            "original-owner", [("owner", new OriginalProbe())]);
        var result = owned.Result(0);
        var lines = ConformanceOriginalObservationOutput.Render(owner).Concat(
            new[] { "before-initialization", "ready", "stopped" }.SelectMany(stage =>
                CompositionPacket(owner.ObservationId, stage)));
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        Assert.Equal(4, proof.RootElement.GetProperty("schemaVersion").GetInt32());
        var snapshots = proof.RootElement.GetProperty("compositionObservations").EnumerateArray().ToArray();
        Assert.Equal(["before-initialization", "ready", "stopped"],
            snapshots.Select(snapshot => snapshot.GetProperty("stage").GetString()!).ToArray());
        Assert.All(snapshots, snapshot =>
            Assert.Equal(owner.ObservationId, snapshot.GetProperty("sourceId").GetGuid()));
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("foreign-source")]
    [InlineData("unknown-stage")]
    [InlineData("unknown-counter")]
    [InlineData("missing-counter")]
    [InlineData("negative-counter")]
    [InlineData("oversize-counter")]
    [InlineData("duplicate-counter")]
    [InlineData("duplicate-packet")]
    [InlineData("duplicate-stage")]
    [InlineData("boolean-counter")]
    [InlineData("string-counter")]
    public void Composition_snapshots_reject_foreign_unbounded_and_duplicate_observations(string mutation)
    {
        using var owned = new OwnedInput();
        var owner = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-owner", [("owner", new OriginalProbe())]);
        var packets = CompositionPacket(owner.ObservationId, "ready", mutation);
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', ConformanceOriginalObservationOutput.Render(owner).Concat(packets))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.NotEqual(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        Assert.Empty(Directory.GetFiles(owned.Output, "proof-*.json"));
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("stage")]
    [InlineData("counter-name")]
    [InlineData("negative")]
    [InlineData("oversize")]
    public void Composition_producer_rejects_unsafe_values_before_any_output(string mutation)
    {
        using var owned = new OwnedInput();
        var owner = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-owner", [("owner", new OriginalProbe())]);
        var counters = CompositionCounters();
        if (mutation == "counter-name") { counters.Add("canary-unbounded-value", 0); }
        if (mutation == "negative") { counters["ready"] = -1; }
        if (mutation == "oversize") { counters["ready"] = 1_000_001; }
        var output = new CapturedOutput();
        var error = Assert.Throws<ArgumentException>(() => ConformanceCompositionObservationOutput.Write(
            output, owner, mutation == "stage" ? "canary-unbounded-value" : "ready", counters));
        Assert.Equal("ProofMismatch", error.Message);
        Assert.Empty(output.Lines);
    }

    private static IEnumerable<string> CompositionPacket(Guid source, string stage, string? mutation = null)
    {
        var counters = CompositionCounters();
        if (mutation == "unknown-counter") { counters.Add("canary-unbounded-value", 0); }
        if (mutation == "missing-counter") { counters.Remove("admission"); }
        if (mutation == "negative-counter") { counters["protocolRequests"] = -1; }
        if (mutation == "oversize-counter") { counters["protocolRequests"] = 1_000_001; }
        var id = Guid.NewGuid();
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            observationId = id,
            sourceId = mutation == "foreign-source" ? Guid.NewGuid() : source,
            stage = mutation == "unknown-stage" ? "canary-unbounded-value" : stage,
            counters
        });
        if (mutation == "duplicate-counter")
        {
            bytes = Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(bytes).Replace(
                "\"admission\":0", "\"admission\":0,\"admission\":0", StringComparison.Ordinal));
        }
        if (mutation is "boolean-counter" or "string-counter")
        {
            bytes = Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(bytes).Replace(
                "\"admission\":0", mutation == "boolean-counter" ? "\"admission\":true" : "\"admission\":\"0\"",
                StringComparison.Ordinal));
        }
        var result = ConformanceEvidencePacket.Render("hoard-composition-v1", id, bytes).AsEnumerable();
        if (mutation == "duplicate-packet") { result = result.Concat(result.ToArray()); }
        if (mutation == "duplicate-stage") { result = result.Concat(CompositionPacket(source, stage)); }
        return result;
    }

    private static Dictionary<string, int> CompositionCounters() => new(StringComparer.Ordinal)
    {
        ["metadataSingletons"] = 1,
        ["artifactSingletons"] = 1,
        ["metadataReady"] = 0,
        ["artifactReady"] = 0,
        ["ready"] = 0,
        ["admission"] = 0,
        ["disabledRoots"] = 0,
        ["protocolRequests"] = 0,
        ["identityRequests"] = 0,
        ["stopComplete"] = 0,
        ["unsafeActivities"] = 0
    };

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Metadata_arguments_follow_actual_component_sources_even_when_output_precedes_the_assertion(bool before)
    {
        using var owned = new OwnedInput();
        var probe = new OriginalProbe();
        var observation = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-instance",
            [("owner", probe), ("store", probe), ("schema", probe), ("authority", probe), ("controls", probe)]);
        var output = new CapturedOutput();
        if (before) { ConformanceOriginalObservationOutput.Write(output, observation); }
        using var scope = before ? ConformanceOriginalObservationOutput.ObserveMetadataArguments(output, observation) : null;
        ConformanceMetadataArgumentOutput.Record(probe, "continuation-corruption", "OddHex");
        ConformanceMetadataArgumentOutput.Record(probe, "schema-layout", "partial");
        if (!before) { ConformanceOriginalObservationOutput.Write(output, observation); }
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', output.Lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        Assert.Equal(3, proof.RootElement.GetProperty("schemaVersion").GetInt32());
        var arguments = proof.RootElement.GetProperty("metadataArguments").EnumerateArray().ToArray();
        Assert.Equal(2, arguments.Length);
        Assert.Equal(2, arguments.Select(argument => argument.GetProperty("callId").GetGuid()).Distinct().Count());
        Assert.All(arguments, argument =>
        {
            Assert.Equal("original-observation", argument.GetProperty("sourceKind").GetString());
            Assert.Equal(observation.ObservationId, argument.GetProperty("sourceId").GetGuid());
            var role = argument.GetProperty("componentRole").GetString()!;
            Assert.Equal(observation.Components[role].InstanceId, argument.GetProperty("componentInstanceId").GetGuid());
        });
        Assert.Equal(["schema", "store"], arguments.Select(argument =>
            argument.GetProperty("componentRole").GetString()!).Order().ToArray());
        Assert.False(probe.Disposed);
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("continuation-corruption", "canary-unbounded-value")]
    [InlineData("canary-unbounded-kind", "partial")]
    public void Metadata_argument_capture_rejects_unbounded_diagnostics_before_output(string kind, string value)
    {
        var error = Assert.Throws<ArgumentException>(() =>
            ConformanceMetadataArgumentOutput.Record(new OriginalProbe(), kind, value));
        Assert.Equal("ProofMismatch", error.Message);
    }

    [Theory]
    [InlineData("memory")]
    [InlineData("contributor")]
    public async Task Metadata_arguments_bind_actual_factory_origins_without_reference_binding_name_switches(string binding)
    {
        using var owned = new OwnedInput();
        owned.Input.Expected[0] = owned.Input.Expected[0] with { BindingId = binding };
        owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, Json));
        var origin = await BindingContractTests.CaptureMetadataOriginAsync(owned.Input.RunId, "runtime");
        var store = origin.ObservedObjects.Single(component => component.Role == "store").Component;
        ConformanceMetadataArgumentOutput.Record(store, "query-corruption", "AggregateEnd");
        var output = new CapturedOutput();
        ConformanceSessionOriginOutput.Write(output, origin);
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', output.Lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        var argument = Assert.Single(proof.RootElement.GetProperty("metadataArguments").EnumerateArray());
        Assert.Equal("session-origin", argument.GetProperty("sourceKind").GetString());
        Assert.Equal(origin.SessionId, argument.GetProperty("sourceId").GetGuid());
        Assert.Equal(origin.Components["store"].InstanceId, argument.GetProperty("componentInstanceId").GetGuid());
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("sourceId")]
    [InlineData("componentInstanceId")]
    [InlineData("componentRole")]
    [InlineData("argumentValue")]
    [InlineData("caseId")]
    [InlineData("runId")]
    [InlineData("duplicate")]
    public void Metadata_argument_packets_reject_foreign_roles_sources_values_and_duplicate_calls(string mutation)
    {
        using var owned = new OwnedInput();
        var probe = new OriginalProbe();
        var observation = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory", "original-instance",
            [("owner", probe), ("store", probe), ("schema", probe), ("authority", probe), ("controls", probe)]);
        var call = Guid.NewGuid();
        var argument = JsonSerializer.SerializeToNode(new
        {
            schemaVersion = 1,
            runId = owned.Input.RunId,
            caseId = "runtime",
            callId = call,
            sourceKind = "original-observation",
            sourceId = observation.ObservationId,
            componentRole = "store",
            componentInstanceId = observation.Components["store"].InstanceId,
            argumentKind = "lease-expiry",
            argumentValue = "Renew"
        })!.AsObject();
        if (mutation is "sourceId" or "componentInstanceId" or "runId") { argument[mutation] = Guid.NewGuid(); }
        else if (mutation == "componentRole") { argument[mutation] = "schema"; }
        else if (mutation == "argumentValue") { argument[mutation] = "canary-unbounded-value"; }
        else if (mutation == "caseId") { argument[mutation] = "foreign"; }
        var packets = ConformanceEvidencePacket.Render(
            ConformanceMetadataArgumentOutput.Prefix, call, JsonSerializer.SerializeToUtf8Bytes(argument));
        var lines = ConformanceOriginalObservationOutput.Render(observation).Concat(packets);
        if (mutation == "duplicate") { lines = lines.Concat(packets); }
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', lines)));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.NotEqual(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        Assert.Empty(Directory.GetFiles(owned.Output, "proof-*.json"));
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Metadata_argument_sources_drain_once_and_release_reused_components(bool deferred)
    {
        using var owned = new OwnedInput();
        var component = new OriginalProbe();
        var first = ArgumentObservation(owned, component, component);
        var second = ArgumentObservation(owned, component, component, first);
        var firstOutput = new CapturedOutput();
        if (deferred) { ConformanceOriginalObservationOutput.Write(firstOutput, first); }
        using (var scope = deferred ? ConformanceOriginalObservationOutput.ObserveMetadataArguments(firstOutput, first) : null)
        { ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Renew"); }
        if (!deferred) { ConformanceOriginalObservationOutput.Write(firstOutput, first); }
        var firstCount = firstOutput.Lines.Count;
        var secondOutput = new CapturedOutput();
        ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Release");
        ConformanceOriginalObservationOutput.Write(secondOutput, second);
        Assert.Equal(firstCount, firstOutput.Lines.Count);
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', firstOutput.Lines.Concat(secondOutput.Lines))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        var arguments = proof.RootElement.GetProperty("metadataArguments").EnumerateArray().ToArray();
        Assert.Equal(2, arguments.Length);
        Assert.Equal(first.ObservationId, arguments.Single(argument =>
            argument.GetProperty("argumentValue").GetString() == "Renew").GetProperty("sourceId").GetGuid());
        Assert.Equal(second.ObservationId, arguments.Single(argument =>
            argument.GetProperty("argumentValue").GetString() == "Release").GetProperty("sourceId").GetGuid());
    }

    [Fact]
    public void Metadata_argument_scope_overlap_rolls_back_without_replacing_either_owner()
    {
        using var owned = new OwnedInput();
        var firstStore = new OriginalProbe();
        var secondStore = new OriginalProbe();
        var schema = new OriginalProbe();
        var first = ArgumentObservation(owned, firstStore, schema);
        var second = ArgumentObservation(owned, secondStore, schema, first);
        var firstOutput = new CapturedOutput();
        var secondOutput = new CapturedOutput();
        ConformanceOriginalObservationOutput.Write(firstOutput, first);
        using var scope = ConformanceOriginalObservationOutput.ObserveMetadataArguments(firstOutput, first);
        var error = Assert.Throws<InvalidOperationException>(() =>
            ConformanceOriginalObservationOutput.ObserveMetadataArguments(secondOutput, second));
        Assert.Equal("OwnershipInvalid", error.Message);
        ConformanceMetadataArgumentOutput.Record(schema, "schema-layout", "partial");
        ConformanceMetadataArgumentOutput.Record(secondStore, "lease-expiry", "Release");
        ConformanceOriginalObservationOutput.Write(secondOutput, second);
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', firstOutput.Lines.Concat(secondOutput.Lines))));
        using var recorder = owned.Open();
        recorder.Observe(result);
        recorder.Complete();
        Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
    }

    [Fact]
    public async Task Metadata_argument_scope_closure_joins_inflight_output_and_detaches_both_roles()
    {
        using var owned = new OwnedInput();
        var component = new OriginalProbe();
        var source = ArgumentObservation(owned, component, component);
        using var entered = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        var output = new CapturedOutput(line =>
        {
            if (line.StartsWith(ConformanceMetadataArgumentOutput.Prefix + ":", StringComparison.Ordinal))
            {
                entered.Set();
                if (!release.Wait(TimeSpan.FromSeconds(5))) { throw new TimeoutException("OutputLimitExceeded"); }
            }
        });
        ConformanceOriginalObservationOutput.Write(output, source);
        using var scope = ConformanceOriginalObservationOutput.ObserveMetadataArguments(output, source);
        var writing = Task.Run(() => ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Renew"));
        Task? closing = null;
        try
        {
            Assert.True(entered.Wait(TimeSpan.FromSeconds(5)));
            closing = Task.Run(scope.Dispose);
            Assert.NotSame(closing, await Task.WhenAny(closing, Task.Delay(TimeSpan.FromMilliseconds(100))));
        }
        finally
        {
            release.Set();
            await writing.WaitAsync(TimeSpan.FromSeconds(5));
            if (closing is not null) { await closing.WaitAsync(TimeSpan.FromSeconds(5)); }
        }
        var count = output.Lines.Count;
        ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Release");
        ConformanceMetadataArgumentOutput.Record(component, "schema-layout", "partial");
        var next = ArgumentObservation(owned, component, component, source);
        var nextOutput = new CapturedOutput();
        ConformanceOriginalObservationOutput.Write(nextOutput, next);
        Assert.Equal(count, output.Lines.Count);
        Assert.Contains(nextOutput.Lines, line =>
            line.StartsWith(ConformanceMetadataArgumentOutput.Prefix + ":", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Metadata_argument_buffers_and_live_scopes_have_closed_call_bounds(bool deferred)
    {
        using var owned = new OwnedInput();
        var component = new OriginalProbe();
        var observation = ArgumentObservation(owned, component, component);
        using var scope = deferred
            ? ConformanceOriginalObservationOutput.ObserveMetadataArguments(new CapturedOutput(), observation) : null;
        for (var index = 0; index < 128; index++)
        { ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Renew"); }
        var error = Assert.Throws<InvalidOperationException>(() =>
            ConformanceMetadataArgumentOutput.Record(component, "lease-expiry", "Renew"));
        Assert.Equal("OutputLimitExceeded", error.Message);
    }

    private static ConformanceOriginalObservation ArgumentObservation(
        OwnedInput owned, object store, object schema, ConformanceOriginalObservation? previous = null) =>
        ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory", "original-instance",
            [("owner", new OriginalProbe()), ("store", store), ("schema", schema), ("authority", store), ("controls", store)],
            parent: null, previous);

    private sealed class CapturedOutput(Action<string>? beforeWrite = null) : Xunit.Abstractions.ITestOutputHelper
    {
        internal List<string> Lines { get; } = [];
        public void WriteLine(string message)
        {
            beforeWrite?.Invoke(message);
            Lines.Add(message);
        }
        public void WriteLine(string format, params object[] args) =>
            WriteLine(string.Format(System.Globalization.CultureInfo.InvariantCulture, format, args));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Original_observations_are_non_owning_and_distinct_from_typed_session_origins(bool contract)
    {
        using var owned = new OwnedInput();
        var probe = new OriginalProbe();
        var components = contract
            ? new (string, object)[] { ("contract", typeof(OriginalProbe)) }
            : [("owner", probe), ("store", probe), ("schema", probe), ("authority", probe), ("controls", probe)];
        var observation = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            contract ? "loaded-contract" : "original-instance", components);
        Assert.False(probe.Disposed);
        if (!contract)
        {
            Assert.Single(observation.Components.Values.Select(value => value.InstanceId).Distinct());
        }
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', ConformanceOriginalObservationOutput.Render(observation))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        Assert.Equal(2, proof.RootElement.GetProperty("schemaVersion").GetInt32());
        Assert.Empty(proof.RootElement.GetProperty("sessionOrigins").EnumerateArray());
        var captured = Assert.Single(proof.RootElement.GetProperty("originalObservations").EnumerateArray());
        Assert.Equal(observation.ObservationId, captured.GetProperty("observationId").GetGuid());
        Assert.Equal(observation.TestIdentity, captured.GetProperty("testIdentity").GetString());
        Assert.False(probe.Disposed);
        AssertSafe(owned.Output);
    }

    private sealed class OriginalProbe : IDisposable
    {
        internal bool Disposed { get; private set; }
        public void Dispose() => Disposed = true;
        public override bool Equals(object? obj) => throw new InvalidOperationException("canary-equality");
        public override int GetHashCode() => throw new InvalidOperationException("canary-hash");
        public override string ToString() => throw new InvalidOperationException("canary-rendering");
    }

    [Fact]
    public void Original_forests_preserve_actual_aliases_without_inventing_reopen_edges()
    {
        using var owned = new OwnedInput();
        var authority = new OriginalProbe();
        var owners = Enumerable.Range(0, 3).Select(_ => new OriginalProbe()).ToArray();
        (string, object)[] Components(int index) =>
            [("owner", owners[index]), ("store", owners[index]), ("schema", owners[index]),
             ("authority", authority), ("controls", owners[index])];
        var first = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-instance", Components(0));
        var second = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-instance", Components(1), parent: null, previous: first);
        var reopened = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-instance", Components(2), parent: first, previous: second);
        Assert.Null(second.ParentObservationId);
        Assert.Equal("create", second.Operation);
        Assert.Equal(first.ObservationId, reopened.ParentObservationId);
        Assert.Equal("reopen", reopened.Operation);
        Assert.Equal(3, new[] { first, second, reopened }
            .Select(observation => observation.Components["owner"].InstanceId).Distinct().Count());
        Assert.All(new[] { first, second, reopened }, observation =>
            Assert.Equal(first.Components["authority"].InstanceId, observation.Components["authority"].InstanceId));
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "foreign", first.TestIdentity, "memory",
            "original-instance", Components(2), parent: null, previous: first));
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-instance", Components(0), parent: null, previous: second));
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n',
            new[] { first, second, reopened }.SelectMany(observation => ConformanceOriginalObservationOutput.Render(observation)))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        Assert.Equal(3, proof.RootElement.GetProperty("originalObservations").GetArrayLength());
        Assert.All(owners.Append(authority), probe => Assert.False(probe.Disposed));
        AssertSafe(owned.Output);
    }

    [Fact]
    public void Original_owner_observations_do_not_fabricate_missing_sessions_or_interfaces()
    {
        using var owned = new OwnedInput();
        var firstOwner = new OriginalProbe();
        var secondOwner = new OriginalProbe();
        var first = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", owned.Input.Expected[0].TestIdentity, "memory",
            "original-owner", [("owner", firstOwner)]);
        var second = ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-owner", [("owner", secondOwner)], parent: null, previous: first);
        Assert.Null(second.ParentObservationId);
        Assert.Equal("create", second.Operation);
        Assert.Equal(["owner"], first.Components.Keys);
        Assert.NotEqual(first.Components["owner"].InstanceId, second.Components["owner"].InstanceId);
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-instance", [("owner", firstOwner)]));
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-owner", [("owner", firstOwner), ("store", firstOwner)]));
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-owner", [("owner", secondOwner)], parent: first));
        Assert.Throws<ArgumentException>(() => ConformanceOriginalObservation.Capture(
            owned.Input.RunId, "runtime", first.TestIdentity, "memory",
            "original-owner", [("owner", firstOwner)], parent: null, previous: second));
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n',
            new[] { first, second }.SelectMany(observation => ConformanceOriginalObservationOutput.Render(observation)))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        Assert.Empty(proof.RootElement.GetProperty("sessionOrigins").EnumerateArray());
        Assert.Equal(2, proof.RootElement.GetProperty("originalObservations").GetArrayLength());
        Assert.False(firstOwner.Disposed);
        Assert.False(secondOwner.Disposed);
        AssertSafe(owned.Output);
    }

    [Fact]
    public async Task Origin_output_is_bound_to_the_actual_result_proof_without_private_component_labels()
    {
        using var owned = new OwnedInput();
        var origin = await BindingContractTests.CaptureMetadataOriginAsync(owned.Input.RunId, "runtime");
        var result = owned.Result(0);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', ConformanceSessionOriginOutput.Render(origin))));
        using (var recorder = owned.Open())
        {
            recorder.Observe(result);
            recorder.Complete();
            Assert.Equal(ConformanceDiagnosticCode.None, recorder.Diagnostic);
        }
        using var proof = JsonDocument.Parse(File.ReadAllBytes(Directory.GetFiles(owned.Output, "proof-*.json").Single()));
        var captured = Assert.Single(proof.RootElement.GetProperty("sessionOrigins").EnumerateArray());
        Assert.Equal(origin.SessionId, captured.GetProperty("sessionId").GetGuid());
        Assert.Equal(owned.Input.Expected[0].CaseId, captured.GetProperty("caseId").GetString());
        Assert.All(captured.GetProperty("components").EnumerateObject(), component =>
            Assert.False(component.Value.TryGetProperty("assemblyName", out _)));
        AssertSafe(owned.Output);
    }

    [Theory]
    [InlineData("missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("digest", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("case", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("replay", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("raw", ConformanceDiagnosticCode.ProofMismatch)]
    [InlineData("instance", ConformanceDiagnosticCode.ProofMismatch)]
    public async Task Invalid_origin_output_retains_prior_execution_without_accepting_replay_or_foreign_case(
        string mutation, ConformanceDiagnosticCode code)
    {
        using var owned = new OwnedInput(2);
        var first = await BindingContractTests.CaptureMetadataOriginAsync(owned.Input.RunId, "runtime");
        var firstResult = owned.Result(0);
        firstResult.Messages.Add(new(TestResultMessage.StandardOutCategory,
            string.Join('\n', ConformanceSessionOriginOutput.Render(first))));
        using var recorder = owned.Open();
        recorder.Observe(firstResult);
        var before = File.ReadAllBytes(Path.Combine(owned.Output, "witnesses.jsonl"));
        var other = mutation == "replay" ? first
            : await BindingContractTests.CaptureMetadataOriginAsync(owned.Input.RunId, mutation == "case" ? "foreign" : "runtime");
        var packets = ConformanceSessionOriginOutput.Render(other).ToArray();
        if (mutation == "missing") { packets = packets[..^1]; }
        if (mutation == "digest")
        {
            var fields = packets[0].Split(':');
            fields[4] = new string('0', 64);
            packets[0] = string.Join(':', fields);
        }
        if (mutation is "raw" or "instance")
        {
            var body = System.Text.Json.Nodes.JsonNode.Parse(Convert.FromBase64String(
                string.Concat(packets.Select(packet => packet.Split(':')[5]))))!;
            if (mutation == "raw") { body["privatePath"] = "/private/canary"; }
            else
            {
                body["components"]!["store"]!["instanceId"] = first.Components["store"].InstanceId.ToString("D");
                body["components"]!["store"]!["typeSha256"] = new string('0', 64);
            }
            var bytes = JsonSerializer.SerializeToUtf8Bytes(body);
            var encoded = Convert.ToBase64String(bytes);
            var count = (encoded.Length + 511) / 512;
            packets = Enumerable.Range(0, count).Select(index =>
                $"{ConformanceSessionOriginOutput.Prefix}:{other.SessionId:D}:{index}:{count}:{Hash(bytes)}:"
                + encoded.Substring(index * 512, Math.Min(512, encoded.Length - index * 512))).ToArray();
        }
        var result = owned.Result(1);
        result.Messages.Add(new(TestResultMessage.StandardOutCategory, string.Join('\n', packets)));
        recorder.Observe(result);
        recorder.Complete();
        Assert.Equal(code, recorder.Diagnostic);
        Assert.Equal(before, File.ReadAllBytes(Path.Combine(owned.Output, "witnesses.jsonl")));
        AssertSafe(owned.Output);
    }

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

    [Theory]
    [InlineData("Assert.True() Failure")]
    [InlineData("Assert.IsType() Failure")]
    public void Assertion_proof_requires_both_frozen_symbol_and_xunit_prefix_and_never_retains_raw_text(
        string assertionPrefix)
    {
        using var owned = new OwnedInput(2);
        using var recorder = owned.Open();
        var assertion = owned.Result(0, TestOutcome.Failed);
        assertion.ErrorMessage = assertionPrefix + "\ncanary-secret-provider-text";
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

    internal static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    internal sealed class OwnedInput : IDisposable
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

        internal OwnedInput(int count = 1, string purpose = "execution", string binding = "memory")
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
                    $"Hoard.Frozen.Check(value: {index})", "Hoard.Frozen.Check", "tests", "fixture", binding, "matrix",
                    "Hoard.Testing.Conformance.FrozenAssertion.Check", "runtime")).ToArray(), purpose);
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
