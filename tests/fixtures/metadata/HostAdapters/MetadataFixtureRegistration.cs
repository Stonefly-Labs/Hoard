using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Fixtures.Metadata.Hosting;

public sealed class MetadataFixtureProvider : IMetadataProvider;

public static class MetadataFixtureRegistration
{
    public static HoardBuilder AddMetadataFixture(this HoardBuilder builder, string id = "fixture.metadata") =>
        builder.AddMetadataFixture<MetadataFixtureProvider>(id);

    public static HoardBuilder AddMetadataFixture<TProvider>(this HoardBuilder builder, string id) where TProvider : class, IMetadataProvider =>
        builder.AddModule<TProvider>(new()
        {
            Id = id,
            Category = ModuleCategory.Metadata,
            Version = "0.1.0",
            Compatibility = new()
            {
                HostRange = "[0.1.0,0.2.0)",
                AbstractionsRange = "[0.1.0,0.2.0)",
                AllowPrereleaseHost = false,
                AllowPrereleaseAbstractions = false
            },
            Dependencies = [],
            Capabilities = [],
            Endpoints = [],
            Health = [],
            Configuration =
            [
                new() { Key = "provider", Description = "Test-only metadata composition.", Required = true, SecretReference = false },
                new() { Key = "createempty", Description = "Explicit empty-fixture creation.", Required = true, SecretReference = false },
                new() { Key = "databasepath", Description = "Private SQLite fixture path.", Required = false, SecretReference = false }
            ],
            Provenance = new() { Publisher = "Hoard metadata acceptance", SupportStatus = ModuleSupportStatus.Fixture }
        })
        .AddModuleLifecycle<TProvider, MetadataFixtureModule>()
        .AddModuleConfiguration<TProvider>(new(1,
        [
            new("provider", HoardOptionType.String, true) { AllowedValues = ["sqlite", "memory"] },
            new("createempty", HoardOptionType.Boolean, true),
            new("databasepath", HoardOptionType.String) { MinimumLength = 1, MaximumLength = 4096 }
        ]));
}
