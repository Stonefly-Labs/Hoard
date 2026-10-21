using Hoard.Hosting;
using Hoard.Hosting.Composition;

namespace Hoard.Composition.Tests;

public class RuntimeCompatibilityTests
{
    [Theory]
    [InlineData("host", false)]
    [InlineData("abstractions", false)]
    [InlineData("malformed", false)]
    [InlineData("prerelease-blocked", false)]
    [InlineData("prerelease-allowed", true)]
    public void Selected_modules_validate_both_platform_axes_without_activation(string kind, bool supported)
    {
        LifecycleFixtures.Reset();
        var registry = LifecycleFixtures.Registry();
        foreach (var descriptor in registry.Services.Where(item => item.ImplementationInstance is HoardModuleRegistration).ToArray())
        {
            var registration = (HoardModuleRegistration)descriptor.ImplementationInstance!;
            registry.Services.Remove(descriptor);
            var compatibility = registration.Declaration.Compatibility with
            {
                HostRange = kind == "host" ? "[9.0.0,10.0.0)" : "[0.1.0,0.2.0)",
                AbstractionsRange = kind == "abstractions" ? "[9.0.0,10.0.0)" : "[0.1.0,0.2.0)",
                AllowPrereleaseHost = kind == "prerelease-allowed"
            };
            registry.Services.Add(Microsoft.Extensions.DependencyInjection.ServiceDescriptor.Singleton(
                registration with { Declaration = registration.Declaration with { Compatibility = compatibility } }));
        }
        var versions = LifecycleFixtures.Versions with
        { HostVersion = kind == "malformed" ? "credential=seeded-secret" : kind.StartsWith("prerelease", StringComparison.Ordinal) ? "0.1.1-rc.1" : "0.1.0" };
        var result = registry.ValidateComposition(LifecycleFixtures.Selection(), versions, new());
        Assert.Equal(supported, result.Composition is not null);
        if (!supported)
        {
            Assert.Contains(result.Diagnostics, item => item.RuleCode == "UnsupportedPlatform");
            LifecycleFixtures.AssertSafe(result.Diagnostics);
        }
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Theory]
    [InlineData("[1.2.0,2.0.0)", "1.4.0", false, true)]
    [InlineData("[1.2.0,2.0.0)", "2.0.0", false, false)]
    [InlineData("[0.1.0,0.2.0)", "0.2.0", false, false)]
    [InlineData("[1.0.0,2.0.0)", "1.5.0-rc.1", false, false)]
    [InlineData("[1.0.0,2.0.0)", "1.5.0-rc.1", true, true)]
    [InlineData("[1.5.0,2.0.0)", "1.5.0-rc.1", true, false)]
    [InlineData("[1.5.0-rc.1,1.5.0]", "1.5.0-rc.2", false, false)]
    [InlineData("[1.2.3]", "1.2.3+build.7", false, true)]
    [InlineData("[1.2.3-RC.1]", "1.2.3-rc.1", true, true)]
    [InlineData("[1.0.0,2.0.0)", "2.0.0-rc.1", true, true)]
    [InlineData("1.*", "1.2.0", true, false)]
    [InlineData("[1.0.0,)", "1.2.0", true, false)]
    [InlineData("(2.0.0,1.0.0]", "1.2.0", true, false)]
    [InlineData("(1.0.0,1.0.0)", "1.0.0", true, false)]
    [InlineData("[1.0]", "1.0.0", true, false)]
    [InlineData("[1.0.0]", "1.0.0.0", true, false)]
    public void Runtime_policy_preserves_F01_interval_and_prerelease_rules(string range, string candidate, bool prerelease, bool supported) =>
        Assert.Equal(supported, RuntimeCompatibility.Axis(range, candidate, prerelease));
}
