using System.Text.Json;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;

namespace Hoard.Conformance.Tests;

public sealed class MetadataBindingTests
{
    [Theory]
    [InlineData("sqlite")]
    [InlineData("memory")]
    public void Extraction_must_preserve_all_frozen_cases_parameters_controls_and_exclusions(string binding) =>
        FrozenAgreement.AssertUnchanged("metadata", binding);

    [Theory]
    [InlineData("sqlite", "complete", ConformanceDiagnosticCode.None)]
    [InlineData("memory", "complete", ConformanceDiagnosticCode.None)]
    [InlineData("sqlite", "missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("memory", "missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("sqlite", "changed", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("memory", "changed", ConformanceDiagnosticCode.WitnessMissing)]
    public void Each_provider_requires_every_exact_corruption_parameter(
        string binding, string mutation, ConformanceDiagnosticCode expected)
    {
        const string method = "Hoard.Metadata.Tests.MetadataFailureTests.MP21_Corrupt_query_dimensions_cannot_disappear_behind_page_filters";
        var entry = Assert.Single(FrozenAgreement.Read("metadata"),
            entry => entry.BindingId == binding && entry.CaseId == "MP-21");
        var witnesses = entry.Witnesses.Where(name => name.Split('(')[0] == method).ToArray();
        Assert.True(witnesses.Length > 1);
        using var owned = new RuntimeLoggerTests.OwnedInput(witnesses.Length, purpose: "discovery");
        FrozenAgreement.Select(owned, entry, witnesses);
        using var recorder = owned.Open();
        var count = mutation == "missing" ? witnesses.Length - 1 : witnesses.Length;
        for (var index = 0; index < count; index++)
        {
            var test = owned.Result(index).TestCase;
            if (mutation == "changed" && index == count - 1)
            { test.DisplayName = method + "(shape: \"provider-selected\")"; }
            recorder.ObserveDiscovery(test);
        }
        recorder.Complete();
        Assert.Equal(expected, recorder.Diagnostic);
        Assert.Equal(mutation == "complete" ? witnesses.Length : witnesses.Length - 1,
            File.ReadAllLines(Path.Combine(owned.Output, "discovered.jsonl")).Length);
        Assert.False(File.Exists(Path.Combine(owned.Output, "witnesses.jsonl")));
    }

    [Theory]
    [InlineData("sqlite")]
    [InlineData("memory")]
    public void Provider_cannot_replace_owned_expectations_with_a_shortened_passing_manifest(string binding)
    {
        var entry = Assert.Single(FrozenAgreement.Read("metadata"),
            entry => entry.BindingId == binding && entry.CaseId == "MP-21");
        using var owned = new RuntimeLoggerTests.OwnedInput(entry.Witnesses.Length, purpose: "discovery");
        FrozenAgreement.Select(owned, entry, entry.Witnesses);
        File.WriteAllText(owned.ManifestPath, JsonSerializer.Serialize(
            owned.Input with { Expected = [owned.Input.Expected[0]] }, RuntimeLoggerTests.Json));
        Assert.Equal("InputChanged", Assert.Throws<InvalidDataException>(() => owned.Open()).Message);
        Assert.False(Directory.Exists(owned.Output));
        FrozenAgreement.AssertUnchanged("metadata", binding);
    }

    [Theory]
    [InlineData("sqlite")]
    [InlineData("memory")]
    public void Missing_logical_hook_rejects_instead_of_reducing_the_selected_agreement(string binding)
    {
        var required = ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata);
        foreach (var missing in required)
        {
            var declaration = new ConformanceBindingDeclaration(binding, ConformanceCategory.Metadata,
                "Hoard.Fixture", "0.1.0", new string('a', 64), ["common-logical", "exclude:MP-21"],
                required.Where(fault => fault != missing));
            Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(
                () => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata)).Message);
        }
        FrozenAgreement.AssertUnchanged("metadata", binding);
    }
}
