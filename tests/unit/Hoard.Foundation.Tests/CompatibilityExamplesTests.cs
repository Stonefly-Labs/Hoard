namespace Hoard.Foundation.Tests;

public class CompatibilityExamplesTests
{
    [Theory]
    [InlineData("C-01", "[1.2.0,2.0.0)", "1.4.0", false, true)]
    [InlineData("C-02", "[1.2.0,2.0.0)", "2.0.0", false, false)]
    [InlineData("C-03", "", "1.0.0", false, false)]
    [InlineData("C-04", "[0.1.0,0.2.0)", "0.2.0", false, false)]
    [InlineData("C-07", "[1.0.0,2.0.0)", "1.5.0-rc.1", false, false)]
    [InlineData("C-08", "[1.0.0,2.0.0)", "1.5.0-rc.1", true, true)]
    [InlineData("C-09", "[1.5.0,2.0.0)", "1.5.0-rc.1", true, false)]
    [InlineData("C-10", "[1.5.0-rc.1,1.5.0]", "1.5.0-rc.2", false, false)]
    [InlineData("C-12", "[1.2.3]", "1.2.3+build.7", false, true)]
    [InlineData("C-13", "(2.0.0,1.0.0]", "1.5.0", false, false)]
    [InlineData("inclusive", "[1.0.0,2.0.0]", "2.0.0", false, true)]
    [InlineData("exclusive", "(1.0.0,2.0.0)", "1.0.0", false, false)]
    [InlineData("empty", "(1.0.0,1.0.0)", "1.0.0", false, false)]
    [InlineData("floating", "1.*", "1.0.0", false, false)]
    [InlineData("unbounded", "[1.0.0,)", "1.0.0", false, false)]
    [InlineData("bare", "1.0.0", "1.0.0", false, false)]
    [InlineData("absent", null, "1.0.0", false, false)]
    [InlineData("case", "[1.0.0-RC.1]", "1.0.0-rc.1", true, true)]
    [InlineData("unnormalized", "[1.0]", "1.0.0", false, false)]
    public void Axis_examples_follow_bounded_intervals_and_explicit_prerelease_flags(
        string name, string? range, string candidate, bool prerelease, bool expected)
    {
        Assert.Equal(expected, CompatibilityExampleEvaluator.Axis(range, candidate, prerelease));
        Assert.NotEmpty(name);
    }

    [Theory]
    [InlineData("C-01", "1.4.0", "1.3.2", false, false, true)]
    [InlineData("C-11", "1.5.0-rc.1", "1.5.0-rc.1", true, false, false)]
    [InlineData("C-18", "1.5.0-rc.1", "1.5.0", false, false, false)]
    public void Host_and_abstractions_axes_have_independent_flags(
        string name, string host, string abstractions, bool allowHost, bool allowAbstractions, bool expected)
    {
        Assert.Equal(expected, CompatibilityExampleEvaluator.Platform(
            name == "C-18" ? "0.1.0-beta.1" : "1.0.0",
            "[1.2.0,2.0.0)", host, allowHost, "[1.2.0,2.0.0)", abstractions, allowAbstractions));
    }

    [Theory]
    [InlineData("C-14", false, "absent", "1.5.0", false, false, false)]
    [InlineData("C-14-outside", false, "enabled", "2.0.0", false, false, false)]
    [InlineData("C-15", true, "absent", "1.5.0", false, true, false)]
    [InlineData("C-19", true, "enabled", "1.5.0", false, true, true)]
    [InlineData("C-20", true, "enabled", "2.0.0", false, false, false)]
    [InlineData("C-21", true, "enabled", "1.5.0-rc.1", false, false, false)]
    [InlineData("C-22", true, "enabled", "1.5.0-rc.1", true, true, true)]
    [InlineData("C-23", true, "installed-disabled", "2.0.0", false, true, false)]
    [InlineData("C-23-registered", true, "registered-disabled", "2.0.0", false, true, false)]
    public void Dependency_examples_never_enable_or_repair_unavailable_or_incompatible_targets(
        string name, bool optional, string selection, string candidate, bool prerelease, bool supported, bool integration)
    {
        var result = CompatibilityExampleEvaluator.Dependency(optional, selection, "[1.0.0,2.0.0)", candidate, prerelease);
        Assert.Equal(supported, result.Supported);
        Assert.Equal(integration, result.IntegrationAvailable);
        Assert.Equal(selection, result.Selection);
        Assert.NotEmpty(result.Reason);
        Assert.NotEmpty(name);
    }
}
