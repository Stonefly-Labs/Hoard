using System.Collections.Immutable;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Conformance.Tests;

public sealed class BindingContractTests
{
    [Theory]
    [InlineData(ConformanceCategory.Metadata)]
    [InlineData(ConformanceCategory.Artifacts)]
    public void Missing_mandatory_faults_cannot_reduce_the_common_agreement(ConformanceCategory category)
    {
        var faults = ConformanceBindingAdmission.RequiredFaults(category);
        foreach (var missing in faults)
        {
            var declaration = Declare(category, faults.Where(fault => fault != missing));
            var failure = Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, category));
            Assert.Equal("BindingInvalid", failure.Message);
        }
        ConformanceBindingAdmission.Validate(Declare(category, faults), category);
    }

    [Fact]
    public void Admission_copies_declarations_and_never_accepts_provider_selected_exclusions()
    {
        var capabilities = new List<string> { "common-logical" };
        var faults = ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata).ToList();
        var declaration = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0",
            new string('a', 64), capabilities, faults);
        capabilities.Clear();
        faults.Clear();
        Assert.Equal<string>(["common-logical"], declaration.Capabilities);
        ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata);
        Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Artifacts));
        var expected = ConformanceCatalog.Expand("metadata");
        var mandatory = expected.Where(entry => entry.BindingId == "memory"
            && entry.CaseId.StartsWith("MP-", StringComparison.Ordinal) && entry.Exclusion is null);
        Assert.All(mandatory, entry => Assert.NotEmpty(entry.Witnesses.Concat(entry.Controls)));
        Assert.DoesNotContain(mandatory, entry => entry.CaseId == "MP-36");
        Assert.Contains(mandatory, entry => entry.CaseId == "MP-37");
        Assert.Contains(mandatory, entry => entry.CaseId == "MP-48");
    }

    [Fact]
    public void Durable_metadata_requires_backup_controls_in_addition_to_logical_faults()
    {
        var declaration = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0", new string('a', 64),
            ["common-logical", "durable-local-process-crash"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata));
        var repaired = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0", new string('a', 64),
            ["common-logical", "durable-local-process-crash"],
            declaration.Faults.Add(ConformanceFault.BackupRestore));
        ConformanceBindingAdmission.Validate(repaired, ConformanceCategory.Metadata);
    }

    [Fact]
    public void Released_observations_cannot_stand_in_for_retained_ownership()
    {
        var resources = new List<string> { "owned-resource" };
        var retained = new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, resources,
            ConformanceDiagnosticCode.CleanupIncomplete);
        resources.Clear();
        Assert.Equal<string>(["owned-resource"], retained.ResourceIds);
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, []));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, ["same", "same"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, ["owned"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Released, ["owned"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Released, [],
            ConformanceDiagnosticCode.CleanupIncomplete));
        Assert.Equal(ConformanceDiagnosticCode.CleanupIncomplete, retained.Reason);
    }

    [Fact]
    public void Fault_observations_reject_private_paths_invalid_counts_and_unknown_states()
    {
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "/private/synthetic-canary", 0, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            (ConformanceFault)int.MaxValue, "capacity", 0, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", -1, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 0, (ConformanceOwnershipState)int.MaxValue));
    }

    [Fact]
    public async Task Evidence_buffer_preserves_observation_order_without_mutable_snapshots()
    {
        var buffer = new ConformanceEvidenceBuffer();
        var first = new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 1, ConformanceOwnershipState.Active);
        await buffer.ObserveAsync(first, default);
        var snapshot = buffer.Snapshot();
        var second = new ConformanceFaultObservation(
            ConformanceFault.CleanupFailure, "cleanup", 2, ConformanceOwnershipState.Retained);
        await buffer.ObserveAsync(second, default);
        Assert.Equal<ConformanceFaultObservation>([first], snapshot);
        Assert.Equal<ConformanceFaultObservation>([first, second], buffer.Snapshot());
    }

    [Fact]
    public async Task Evidence_buffer_rejects_cancellation_and_overflow_without_losing_prior_observations()
    {
        var buffer = new ConformanceEvidenceBuffer();
        var observation = new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 1, ConformanceOwnershipState.Active);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(async () =>
            await buffer.ObserveAsync(observation, cancelled.Token));
        Assert.Empty(buffer.Snapshot());
        for (var number = 0; number < 10_000; number++)
        {
            await buffer.ObserveAsync(observation, default);
        }
        var failure = await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await buffer.ObserveAsync(observation, default));
        Assert.Equal("OutputLimitExceeded", failure.Message);
        Assert.Equal(10_000, buffer.Snapshot().Length);
        Assert.All(buffer.Snapshot(), observed => Assert.Equal(observation, observed));
    }

    [Fact]
    public void Catalog_exclusion_cannot_be_fabricated_as_a_runtime_execution()
    {
        var expected = ConformanceCatalog.Expand("metadata").First(entry => !entry.Witnesses.IsEmpty);
        Assert.Throws<ArgumentException>(() => new ConformanceRuntimeWitness(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), expected, expected.Witnesses[0],
            new string('a', 64), new string('b', 64), new string('c', 64),
            TimeSpan.Zero, TimeSpan.FromSeconds(1), ConformanceWitnessStatus.NotApplicable,
            new string('d', 64)));
    }

    [Fact]
    public async Task Diagnostic_projection_accepts_only_closed_codes_and_numeric_measurements()
    {
        await using var output = new MemoryStream();
        await Assert.ThrowsAsync<ArgumentException>(async () =>
            await ConformanceDiagnostic.WriteAsync(output, (ConformanceDiagnosticCode)int.MaxValue, 1, default));
        Assert.Equal(0, output.Length);
        await ConformanceDiagnostic.WriteAsync(output, ConformanceDiagnosticCode.CleanupIncomplete, 1, default);
        Assert.Equal("{\"event\":\"control\",\"code\":\"CleanupIncomplete\",\"value\":1}\n",
            System.Text.Encoding.UTF8.GetString(output.ToArray()));
    }

    [Fact]
    public void Corruption_observations_cannot_export_private_values_as_fingerprints()
    {
        foreach (var input in new[] { "/private/synthetic-canary", new string('A', 64), new string('a', 65), "" })
        {
            var failure = Assert.Throws<ArgumentException>(() => new ConformanceStateFingerprint(input));
            Assert.Equal("BindingInvalid", failure.Message);
        }
        Assert.Equal(new ConformanceStateFingerprint(new string('a', 64)), new ConformanceStateFingerprint(new string('a', 64)));
    }

    private static ConformanceBindingDeclaration Declare(
        ConformanceCategory category, IEnumerable<ConformanceFault> faults) =>
        new("binding", category, "Hoard.Fixture", "0.1.0", new string('a', 64), ["common-logical"], faults);
}
