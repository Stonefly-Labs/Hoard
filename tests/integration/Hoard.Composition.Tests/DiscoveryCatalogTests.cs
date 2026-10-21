using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryCatalogTests
{
    [Theory]
    [InlineData("duplicate")]
    [InlineData("conflict")]
    [InlineData("orphan")]
    [InlineData("owners")]
    [InlineData("evidence")]
    [InlineData("fields")]
    [InlineData("text")]
    public void Invalid_static_associations_reject_before_construction(string defect)
    {
        LifecycleFixtures.Reset();
        var catalog = DiscoveryFixtures.Catalog();
        catalog = defect switch
        {
            "duplicate" => catalog with
            {
                IncludedModules = [
                LifecycleFixtures.Declaration("included", ModuleCategory.Protocol),
                LifecycleFixtures.Declaration("included", ModuleCategory.Protocol)]
            },
            "conflict" => catalog with { IncludedModules = [LifecycleFixtures.Declaration("metadata", ModuleCategory.Artifact)] },
            "orphan" => catalog with { Publications = [new("not-registered")] },
            "owners" => catalog with { Contributions = [catalog.Contributions[0] with { Owners = ["unknown"] }] },
            "evidence" => catalog with { Contributions = [catalog.Contributions[0] with { EvidenceIds = [] }] },
            "fields" => catalog with { Publications = [new("protocol") { Options = [new("not-a-field")] }] },
            "text" => catalog with { Publications = [new("protocol") { Publisher = "<unsafe>" }] },
            _ => throw new InvalidOperationException()
        };
        Assert.Throws<HoardDiscoverySetupException>(() =>
        {
            var builder = DiscoveryFixtures.Registry(catalog: catalog);
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new());
        });
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Theory]
    [InlineData(254, true)]
    [InlineData(255, false)]
    public async Task Module_limit_checks_the_union_before_activation(int included, bool permitted)
    {
        LifecycleFixtures.Reset();
        var catalog = new HoardDiscoveryCatalog("fixture", "0.1.0", "complete")
        {
            IncludedModules = Enumerable.Range(0, included)
                .Select(index => LifecycleFixtures.Declaration($"included-{index}", ModuleCategory.Protocol)).ToImmutableArray()
        };
        var builder = LifecycleFixtures.Registry().AddHoardDiscovery(catalog, new());
        if (!permitted)
        {
            Assert.Throws<HoardDiscoverySetupException>(() =>
                builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()));
            Assert.Empty(LifecycleFixtures.Controls);
            return;
        }
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(composition);
        Assert.Equal(256, lease.Discovery!.Capture().Observation!.Modules.Length);
    }

    [Fact]
    public void A_second_validation_cannot_silently_change_frozen_registration_metadata()
    {
        LifecycleFixtures.Reset();
        var builder = LifecycleFixtures.Registry().AddHoardDiscovery(new("fixture", "0.1.0", "partial"), new());
        Assert.NotNull(builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition);
        builder.AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity));
        Assert.Throws<HoardDiscoverySetupException>(() =>
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()));
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Theory]
    [InlineData("id", 128, true)]
    [InlineData("id", 129, false)]
    [InlineData("publisher", 160, true)]
    [InlineData("publisher", 161, false)]
    [InlineData("description", 512, true)]
    [InlineData("description", 513, false)]
    public async Task Public_text_bounds_have_valid_and_rejected_counterparts(string field, int length, bool permitted)
    {
        LifecycleFixtures.Reset();
        var included = LifecycleFixtures.Declaration("included", ModuleCategory.Identity) with
        { Configuration = [new() { Key = "label", Description = "Unapproved raw text", Required = false, SecretReference = false }] };
        var catalog = new HoardDiscoveryCatalog(field == "id" ? new string('a', length) : "fixture", "0.1.0", "partial")
        {
            IncludedModules = [included],
            Publications = [new("included")
            {
                Publisher = field == "publisher" ? new string('a', length) : "Approved",
                Options = [new("label") { Description = field == "description" ? new string('a', length) : "Approved" }]
            }]
        };
        if (!permitted)
        {
            Assert.Throws<HoardDiscoverySetupException>(() => LifecycleFixtures.Registry().AddHoardDiscovery(catalog, new()));
            Assert.Empty(LifecycleFixtures.Controls);
            return;
        }
        var builder = LifecycleFixtures.Registry().AddHoardDiscovery(catalog, new());
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        Assert.True(lease.Discovery!.Capture().Success);
    }

    [Theory]
    [InlineData("contributions", 4096, true)]
    [InlineData("contributions", 4097, false)]
    [InlineData("fields", 4096, true)]
    [InlineData("fields", 4097, false)]
    [InlineData("per-module", 64, true)]
    [InlineData("per-module", 65, false)]
    public async Task Collection_bounds_precede_activation_and_never_truncate_success(string kind, int count, bool permitted)
    {
        LifecycleFixtures.Reset();
        var owners = kind == "fields" ? (count + 255) / 256 : kind == "per-module" ? 1 : 64;
        var included = Enumerable.Range(0, owners).Select(index =>
            LifecycleFixtures.Declaration($"included-{index}", ModuleCategory.Protocol) with
            {
                Capabilities = kind == "fields" ? [] : [new() { Id = "inspect", Version = "0.1.0", Description = "Fixture" }],
                Configuration = kind != "fields" ? [] : Enumerable.Range(0, Math.Min(256, count - index * 256))
                    .Select(number => new ConfigurationRequirement
                    { Key = $"field-{number}", Description = "Unapproved", Required = false, SecretReference = false }).ToImmutableArray()
            }).ToImmutableArray();
        var catalog = new HoardDiscoveryCatalog("fixture", "0.1.0", "partial")
        {
            IncludedModules = included,
            Contributions = kind == "fields" ? [] : Enumerable.Range(0, count).Select(number =>
                new DiscoveryContribution("inspect", "0.1.0", $"operation-{number}", [$"included-{(kind == "per-module" ? 0 : number / 64)}"])).ToImmutableArray()
        };
        if (!permitted)
        {
            Assert.Throws<HoardDiscoverySetupException>(() =>
            {
                var invalid = LifecycleFixtures.Registry().AddHoardDiscovery(catalog, new());
                invalid.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
            });
            Assert.Empty(LifecycleFixtures.Controls);
            return;
        }
        var builder = LifecycleFixtures.Registry().AddHoardDiscovery(catalog, new());
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var result = lease.Discovery!.Capture();
        Assert.True(result.Success);
        Assert.Equal(count, kind == "fields" ? result.Observation!.Modules.Sum(module => module.Options.Length)
            : result.Observation!.Modules.Sum(module => module.Capabilities.Length));
    }
}
