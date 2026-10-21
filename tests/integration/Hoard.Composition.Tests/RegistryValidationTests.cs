using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class RegistryValidationTests
{
    [Theory]
    [InlineData("unknown")]
    [InlineData("UPPERCASE-secret")]
    public void Unknown_or_unsafe_selection_fails_without_construction(string id)
    {
        LifecycleFixtures.Reset();
        var validation = LifecycleFixtures.Registry().ValidateComposition(LifecycleFixtures.Selection(id),
            LifecycleFixtures.Versions, new());
        Assert.Null(validation.Composition);
        LifecycleFixtures.AssertSafe(validation.Diagnostics);
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Theory]
    [InlineData("id")]
    [InlineData("enum")]
    [InlineData("version")]
    [InlineData("compatibility")]
    [InlineData("default-dependencies")]
    [InlineData("capabilities")]
    [InlineData("endpoints")]
    [InlineData("health")]
    [InlineData("configuration")]
    [InlineData("provenance")]
    [InlineData("url")]
    [InlineData("self")]
    [InlineData("family")]
    public void Disabled_malformed_declarations_are_not_ignored(string mutation)
    {
        LifecycleFixtures.Reset();
        var declaration = LifecycleFixtures.Declaration("disabled", ModuleCategory.Protocol);
        declaration = mutation switch
        {
            "id" => declaration with { Id = "Credential=seeded-secret" },
            "enum" => declaration with { Category = (ModuleCategory)99 },
            "version" => declaration with { Version = "1.0" },
            "compatibility" => declaration with { Compatibility = null! },
            "default-dependencies" => declaration with { Dependencies = default },
            "capabilities" => declaration with { Capabilities = [new() { Id = "a", Version = "1.0.0", Description = "a" }, new() { Id = "a", Version = "1.0.0", Description = "a" }] },
            "endpoints" => declaration with { Endpoints = [new() { Id = "a", Description = "" }] },
            "health" => declaration with { Health = [null!] },
            "configuration" => declaration with { Configuration = [new() { Key = "key", Description = "a", Required = true, SecretReference = true }, new() { Key = "key", Description = "b", Required = false, SecretReference = false }] },
            "provenance" => declaration with { Provenance = null! },
            "url" => declaration with { Provenance = declaration.Provenance with { SourceUrl = new("https://user:seeded-secret@example.com/?token=seeded-secret") } },
            "self" => declaration with { Dependencies = [new() { ModuleId = "disabled", VersionRange = "[0.1.0]", Optional = true, AllowPrerelease = false }] },
            "family" => declaration with { Category = ModuleCategory.Artifact },
            _ => throw new InvalidOperationException()
        };
        var registry = LifecycleFixtures.Registry().AddModule<LifecycleFixtures.ProtocolProvider>(declaration);
        var result = registry.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        Assert.Null(result.Composition);
        LifecycleFixtures.AssertSafe(result.Diagnostics);
        Assert.DoesNotContain("seeded-secret", System.Text.Json.JsonSerializer.Serialize(result.Diagnostics));
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public void Duplicate_ids_and_duplicate_or_orphan_adapters_fail_even_when_disabled()
    {
        foreach (var kind in new[] { "id", "adapter", "orphan", "missing" })
        {
            var registry = LifecycleFixtures.Registry();
            if (kind == "id") { registry.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("artifact", ModuleCategory.Protocol)); }
            if (kind == "adapter") { registry.AddModuleLifecycle<LifecycleFixtures.ArtifactProvider, LifecycleFixtures.ArtifactModule>(); }
            if (kind == "orphan") { registry.AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>(); }
            if (kind == "missing") { registry.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol)); }
            var result = registry.ValidateComposition(LifecycleFixtures.Selection(kind == "missing" ? ["protocol"] : []),
                LifecycleFixtures.Versions, new());
            Assert.Null(result.Composition);
            LifecycleFixtures.AssertSafe(result.Diagnostics);
        }
    }

    [Fact]
    public void Disabled_structurally_valid_incompatible_registration_needs_no_adapter()
    {
        var declaration = LifecycleFixtures.Declaration("disabled", ModuleCategory.Protocol);
        var registry = LifecycleFixtures.Registry().AddModule<LifecycleFixtures.ProtocolProvider>(declaration with
        { Compatibility = declaration.Compatibility with { HostRange = "[9.0.0,10.0.0)" } });
        var result = registry.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new());
        Assert.Empty(result.Diagnostics);
        Assert.Single(Assert.IsType<HoardValidatedComposition>(result.Composition).DisabledDeclarations);
    }
}
