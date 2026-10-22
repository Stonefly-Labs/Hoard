using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed class ArtifactFixtureProvider : IArtifactProvider;

public static class ArtifactFixtureRegistration
{
    public static HoardBuilder AddArtifactFixture(this HoardBuilder builder, string id = "fixture.artifact") =>
        builder.AddArtifactFixture<ArtifactFixtureProvider>(id);

    public static HoardBuilder AddArtifactFixture<TProvider>(this HoardBuilder builder, string id)
        where TProvider : class, IArtifactProvider =>
        builder.AddModule<TProvider>(new()
        {
            Id = id,
            Category = ModuleCategory.Artifact,
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
                new() { Key = "provider", Description = "Explicit test-only artifact selection.", Required = true, SecretReference = false },
                new() { Key = "root", Description = "Owner-private artifact fixture root.", Required = true, SecretReference = false }
            ],
            Provenance = new() { Publisher = "Hoard artifact acceptance", SupportStatus = ModuleSupportStatus.Fixture }
        })
        .AddModuleLifecycle<TProvider, ArtifactFixtureModule>()
        .AddModuleConfiguration<TProvider>(new(1,
        [
            new("provider", HoardOptionType.String, true) { AllowedValues = ["local", "object"] },
            new("root", HoardOptionType.String, true) { MinimumLength = 1, MaximumLength = 4096 }
        ]));
}
