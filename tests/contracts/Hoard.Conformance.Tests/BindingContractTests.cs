using System.Collections.Immutable;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;
using Hoard.Testing.Conformance.Diagnostics;

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
        var retained = new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, resources);
        resources.Clear();
        Assert.Equal<string>(["owned-resource"], retained.ResourceIds);
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, []));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, ["same", "same"]));
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

    private static ConformanceBindingDeclaration Declare(
        ConformanceCategory category, IEnumerable<ConformanceFault> faults) =>
        new("binding", category, "Hoard.Fixture", "0.1.0", new string('a', 64), ["common-logical"], faults);
}
