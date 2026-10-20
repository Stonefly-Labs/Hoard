using Hoard.Tests;

namespace Hoard.Foundation.Tests;

public class ContractChangeExamplesTests
{
    [Theory]
    [InlineData("C-05", "stable-major", "required", "CS0535")]
    [InlineData("C-06", "pre-1.0-minor", "required", "CS0535")]
    [InlineData("C-16", "stable-major", "", "")]
    [InlineData("C-17", "stable-major", "binary", "MissingMethodException")]
    public void Breaking_changes_require_policy_transition_and_migration_not_just_one_compiling_consumer(
        string id, string transition, string fixture, string diagnostic)
    {
        var example = ContractChangeExamples.All.Single(e => e.Id == id);
        Assert.False(example.ProposedReleaseValid);
        Assert.Equal(transition, example.RequiredTransition);
        Assert.All(new[] { example.ConsumerImpact, example.ImplementerImpact, example.BinaryImpact,
            example.BehaviorImpact, example.OldRange, example.NewRange, example.Migration,
            example.Qualification, example.Rollback }, value => Assert.False(string.IsNullOrWhiteSpace(value)));
        Assert.NotEqual(example.OldRange, example.NewRange);
        if (fixture.Length != 0)
        {
            var proof = FoundationEvidence.Load().GetProperty("breaking").GetProperty(fixture);
            Assert.True(proof.GetProperty("oldSuccess").GetBoolean());
            Assert.False(proof.GetProperty("newSuccess").GetBoolean());
            Assert.Contains(diagnostic, proof.GetProperty("output").GetString());
            if (fixture == "binary")
            {
                Assert.True(proof.GetProperty("migratedSourceSuccess").GetBoolean());
            }
        }
    }
}
