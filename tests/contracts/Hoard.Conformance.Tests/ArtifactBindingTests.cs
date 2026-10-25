using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;
using Hoard.Testing.Conformance.Diagnostics;

namespace Hoard.Conformance.Tests;

public sealed class ArtifactBindingTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public void Extraction_must_preserve_all_frozen_streaming_authority_and_recovery_obligations(string binding) =>
        FrozenAgreement.AssertUnchanged("artifacts", binding);

    [Theory]
    [InlineData("local", "complete", ConformanceDiagnosticCode.None)]
    [InlineData("object", "complete", ConformanceDiagnosticCode.None)]
    [InlineData("local", "missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("object", "missing", ConformanceDiagnosticCode.EvidenceIncomplete)]
    [InlineData("local", "foreign", ConformanceDiagnosticCode.WitnessMissing)]
    [InlineData("object", "foreign", ConformanceDiagnosticCode.WitnessMissing)]
    public void Both_streaming_handoff_rows_are_required_and_cannot_borrow_the_other_provider(
        string binding, string mutation, ConformanceDiagnosticCode expected)
    {
        var groups = FrozenAgreement.ParameterizedGroups("artifacts", binding).ToArray();
        Assert.NotEmpty(groups);
        foreach (var (entry, witnesses) in groups)
        {
            var method = witnesses[0].Split('(')[0];
            using var owned = new RuntimeLoggerTests.OwnedInput(witnesses.Length, purpose: "discovery");
            FrozenAgreement.Select(owned, entry, witnesses);
            using var recorder = owned.Open();
            var count = mutation == "missing" ? witnesses.Length - 1 : witnesses.Length;
            for (var index = 0; index < count; index++)
            {
                var test = owned.Result(index).TestCase;
                if (mutation == "foreign" && index == count - 1)
                {
                    var other = binding == "local" ? "object" : "local";
                    test.DisplayName = witnesses[index].Contains($"provider: \"{binding}\"", StringComparison.Ordinal)
                        ? witnesses[index].Replace($"provider: \"{binding}\"", $"provider: \"{other}\"",
                            StringComparison.Ordinal)
                        : method + "(shape: \"provider-selected\")";
                    Assert.NotEqual(witnesses[index], test.DisplayName);
                }
                recorder.ObserveDiscovery(test);
            }
            recorder.Complete();
            Assert.Equal(expected, recorder.Diagnostic);
            Assert.Equal(mutation == "complete" ? witnesses.Length : witnesses.Length - 1,
                File.ReadAllLines(Path.Combine(owned.Output, "discovered.jsonl")).Length);
            Assert.False(File.Exists(Path.Combine(owned.Output, "witnesses.jsonl")));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public void Missing_authority_or_streaming_fault_hooks_cannot_reduce_the_agreement(string binding)
    {
        var required = ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts);
        foreach (var missing in required)
        {
            var declaration = new ConformanceBindingDeclaration(binding, ConformanceCategory.Artifacts,
                "Hoard.Fixture", "0.1.0", new string('a', 64), ["common-logical", "exclude:AS-15"],
                required.Where(fault => fault != missing));
            Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(
                () => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Artifacts)).Message);
        }
        FrozenAgreement.AssertUnchanged("artifacts", binding);
    }

    [Fact]
    public void Simulation_cannot_take_local_restart_witnesses_or_remove_its_frozen_exclusions()
    {
        var frozen = FrozenAgreement.Read("artifacts");
        var actual = ConformanceCatalog.Expand("artifacts");
        var excluded = frozen.Where(entry => entry.BindingId == "object" && entry.Exclusion is not null).ToArray();
        Assert.NotEmpty(excluded);
        foreach (var entry in excluded)
        {
            var simulation = Assert.Single(actual,
                candidate => candidate.BindingId == "object" && candidate.CaseId == entry.CaseId);
            var local = Assert.Single(actual,
                candidate => candidate.BindingId == "local" && candidate.CaseId == entry.CaseId);
            Assert.Equal(entry.Exclusion, simulation.Exclusion);
            Assert.Equal<string>(entry.Witnesses, simulation.Witnesses);
            Assert.Equal<string>(entry.Controls, simulation.Controls);
            Assert.Null(local.Exclusion);
        }
        FrozenAgreement.AssertUnchanged("artifacts", "object");
    }
}
