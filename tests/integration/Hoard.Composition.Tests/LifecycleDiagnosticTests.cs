using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleDiagnosticTests
{
    [Fact]
    public void Invalid_input_bounding_preserves_safe_actions_and_explicit_omission_counts()
    {
        var builder = LifecycleFixtures.Registry();
        var demands = Enumerable.Range(0, 150).Select(index => new HoardRequiredCapability(
            $"target-{index}", "capability", "[0.1.0]", false)).ToImmutableArray();
        var validation = builder.ValidateComposition(LifecycleFixtures.Selection() with { RequiredCapabilities = demands },
            LifecycleFixtures.Versions, new());
        Assert.Null(validation.Composition);
        Assert.Equal(100, validation.Diagnostics.Length);
        Assert.Equal(50, validation.OmittedCount);
        var diagnostic = new HoardLifecycleDiagnostic("PhaseFailure", "credential=seeded-secret", HoardLifecyclePhase.Initializing,
            Guid.NewGuid(), path: Enumerable.Repeat("unsafe/seeded-secret", 50));
        Assert.Equal(32, diagnostic.DependencyPath.Length);
        Assert.Equal(18, diagnostic.OmittedPathCount);
        Assert.DoesNotContain("seeded-secret", JsonSerializer.Serialize(diagnostic));
        Assert.All(validation.Diagnostics, item =>
        {
            Assert.NotEqual(Guid.Empty, item.CorrelationId);
            Assert.NotEmpty(item.CorrectiveAction);
            Assert.True(item.CorrectiveAction.Length <= 512);
            Assert.Equal(HoardLifecyclePhase.Validating, item.Phase);
        });
    }
}
