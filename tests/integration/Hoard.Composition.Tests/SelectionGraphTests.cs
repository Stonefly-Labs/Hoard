using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class SelectionGraphTests
{
    [Theory]
    [InlineData("compatible", true)]
    [InlineData("absent", false)]
    [InlineData("disabled", false)]
    [InlineData("missing", false)]
    [InlineData("incompatible", false)]
    [InlineData("prerelease-blocked", false)]
    [InlineData("prerelease-allowed", true)]
    public void Capabilities_require_the_correct_enabled_target_and_explicit_version_policy(string kind, bool valid)
    {
        var registry = LifecycleFixtures.Registry();
        var existing = registry.Services.Single(item => item.ImplementationInstance is HoardModuleRegistration registration
            && registration.Declaration.Id == "artifact");
        var registration = (HoardModuleRegistration)existing.ImplementationInstance!;
        registry.Services.Remove(existing);
        registry.Services.Add(Microsoft.Extensions.DependencyInjection.ServiceDescriptor.Singleton(registration with
        {
            Declaration = registration.Declaration with
            {
                Capabilities = [new() { Id = "feature", Version = kind.StartsWith("prerelease", StringComparison.Ordinal)
                ? "1.2.0-rc.1" : "1.2.0", Description = "Fixture" }]
            }
        }));
        registry.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol));
        var selection = LifecycleFixtures.Selection() with
        {
            RequiredCapabilities = [new(kind == "absent" ? "absent" : kind == "disabled" ? "protocol" : "artifact",
                kind == "missing" ? "missing" : "feature", kind == "incompatible" ? "[2.0.0]" : "[1.0.0,2.0.0)",
                kind == "prerelease-allowed")]
        };
        var result = registry.ValidateComposition(selection, LifecycleFixtures.Versions, new());
        Assert.Equal(valid, result.Composition is not null);
        if (!valid)
        {
            Assert.Contains(result.Diagnostics, item => item.RuleCode == "UnsupportedCapability");
            LifecycleFixtures.AssertSafe(result.Diagnostics);
        }
    }

    [Fact]
    public void Unregistered_optional_target_contributes_no_edge_but_required_target_fails()
    {
        foreach (var optional in new[] { true, false })
        {
            LifecycleFixtures.Reset();
            var registry = LifecycleFixtures.Registry()
                .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
                { Dependencies = [new() { ModuleId = "absent", VersionRange = "[0.1.0]", Optional = optional, AllowPrerelease = false }] })
                .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
            var result = registry.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new());
            Assert.Equal(optional, result.Composition is not null);
            if (optional) { Assert.Empty(result.Composition!.ActiveEdges); }
            else
            {
                Assert.Contains(result.Diagnostics, item => item.RuleCode == "MissingDependency");
                LifecycleFixtures.AssertSafe(result.Diagnostics);
            }
            Assert.Empty(LifecycleFixtures.Controls);
        }
    }

    [Fact]
    public void Multiple_protocols_and_identities_are_permitted_but_authoritative_cardinality_is_not_inferred()
    {
        var registry = LifecycleFixtures.Registry()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol))
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
            .AddModule<OtherProtocol>(LifecycleFixtures.Declaration("protocol-other", ModuleCategory.Protocol))
            .AddModuleLifecycle<OtherProtocol, LifecycleFixtures.ProtocolModule>()
            .AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity))
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>()
            .AddModule<OtherIdentity>(LifecycleFixtures.Declaration("identity-other", ModuleCategory.Identity))
            .AddModuleLifecycle<OtherIdentity, LifecycleFixtures.IdentityModule>();
        Assert.NotNull(registry.ValidateComposition(LifecycleFixtures.Selection("protocol", "protocol-other", "identity", "identity-other"),
            LifecycleFixtures.Versions, new()).Composition);
        registry.AddModule<OtherArtifact>(LifecycleFixtures.Declaration("artifact-other", ModuleCategory.Artifact))
            .AddModuleLifecycle<OtherArtifact, LifecycleFixtures.ArtifactModule>()
            .AddModule<OtherMetadata>(LifecycleFixtures.Declaration("metadata-other", ModuleCategory.Metadata))
            .AddModuleLifecycle<OtherMetadata, LifecycleFixtures.MetadataModule>();
        foreach (var selection in new[]
        {
            LifecycleFixtures.Selection() with { EnabledModuleIds = ["metadata"] },
            LifecycleFixtures.Selection("artifact-other"),
            LifecycleFixtures.Selection("metadata-other"),
            LifecycleFixtures.Selection() with { ArtifactModuleId = "artifact-other" }
        })
        {
            var rejected = registry.ValidateComposition(selection, LifecycleFixtures.Versions, new());
            Assert.Null(rejected.Composition);
            Assert.Contains(rejected.Diagnostics, item => item.RuleCode == "InvalidCardinality");
            LifecycleFixtures.AssertSafe(rejected.Diagnostics);
        }
    }

    private sealed class OtherProtocol : IProtocolProvider;
    private sealed class OtherIdentity : IIdentityProvider;
    private sealed class OtherArtifact : IArtifactProvider;
    private sealed class OtherMetadata : IMetadataProvider;

    [Theory]
    [InlineData(false, false, false, false)]
    [InlineData(true, false, false, true)]
    [InlineData(true, true, false, true)]
    [InlineData(true, true, true, false)]
    [InlineData(false, true, false, true)]
    public void Dependencies_require_enabled_compatible_targets_without_auto_enablement(
        bool optional, bool enabled, bool incompatible, bool valid)
    {
        var registry = LifecycleFixtures.Registry();
        var protocol = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Dependencies = [new() { ModuleId = "identity", VersionRange = incompatible ? "[9.0.0]" : "[0.1.0]",
                Optional = optional, AllowPrerelease = false }]
        };
        registry.AddModule<LifecycleFixtures.ProtocolProvider>(protocol)
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        registry.AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity))
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>();
        var validation = registry.ValidateComposition(LifecycleFixtures.Selection(enabled ? ["protocol", "identity"] : ["protocol"]),
            LifecycleFixtures.Versions, new());
        Assert.Equal(valid, validation.Composition is not null);
        if (!valid) { LifecycleFixtures.AssertSafe(validation.Diagnostics); }
        if (valid)
        {
            Assert.Equal(enabled ? 1 : 0, validation.Composition!.ActiveEdges.Length);
            if (enabled)
            {
                Assert.True(validation.Composition.ActivationOrder.IndexOf("identity") <
                    validation.Composition.ActivationOrder.IndexOf("protocol"));
            }
        }
    }

    [Fact]
    public void Selection_order_is_ordinal_and_cardinality_and_capability_are_explicit()
    {
        var registry = LifecycleFixtures.Registry();
        var result = registry.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        Assert.Equal(new[] { "artifact", "metadata" }, result.Composition!.ActivationOrder.ToArray());
        foreach (var selection in new[]
        {
            LifecycleFixtures.Selection() with { EnabledModuleIds = ["artifact"] },
            LifecycleFixtures.Selection() with { MetadataModuleId = "artifact" },
            LifecycleFixtures.Selection() with { EnabledModuleIds = ["artifact", "metadata", "artifact"] },
            LifecycleFixtures.Selection() with { RequiredCapabilities = [new("artifact", "unknown", "[0.1.0]", false)] }
        })
        {
            Assert.Null(registry.ValidateComposition(selection, LifecycleFixtures.Versions, new()).Composition);
        }
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Enabled_required_or_optional_cycle_fails_with_safe_involved_path(bool optional)
    {
        var registry = LifecycleFixtures.Registry();
        var original = registry.Services.Where(d => d.ImplementationInstance is HoardModuleRegistration).ToArray();
        foreach (var descriptor in original)
        {
            var registration = (HoardModuleRegistration)descriptor.ImplementationInstance!;
            registry.Services.Remove(descriptor);
            var target = registration.Declaration.Id == "artifact" ? "metadata" : "artifact";
            registry.Services.Add(Microsoft.Extensions.DependencyInjection.ServiceDescriptor.Singleton(
                registration with
                {
                    Declaration = registration.Declaration with
                    { Dependencies = [new() { ModuleId = target, VersionRange = "[0.1.0]", Optional = optional, AllowPrerelease = false }] }
                }));
        }
        var result = registry.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        Assert.Null(result.Composition);
        Assert.Contains(result.Diagnostics, d => d.RuleCode == "DependencyCycle" && d.DependencyPath.Contains("artifact") && d.DependencyPath.Contains("metadata"));
        LifecycleFixtures.AssertSafe(result.Diagnostics);
    }
}
