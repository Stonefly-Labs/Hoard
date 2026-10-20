using System.Collections.Immutable;
using Hoard.Abstractions.Modules;

public static class Consumer
{
    public static ModuleDescriptor Declaration => new()
    {
        Id = "fixture.declaration",
        Category = ModuleCategory.Protocol,
        Version = "0.1.0",
        Compatibility = new()
        {
            HostRange = "[0.1.0,0.2.0)",
            AbstractionsRange = "[0.1.0,0.2.0)",
            AllowPrereleaseHost = false,
            AllowPrereleaseAbstractions = false
        },
        Dependencies = [new() { ModuleId = "fixture.optional", VersionRange = "[1.0.0]", Optional = true, AllowPrerelease = false }],
        Capabilities = [new() { Id = "fixture.description", Version = "1.0.0", Description = "Declaration example only." }],
        Configuration = [new() { Key = "credentials.reference", Description = "Reference requirement, not a value.", Required = true, SecretReference = true }],
        Endpoints = [new() { Id = "fixture.route", Description = "Responsibility, not a mapped endpoint." }],
        Health = [new() { Id = "fixture.health", Description = "Responsibility, not a live probe.", RequiredForReadiness = true }],
        Provenance = new() { Publisher = "Hoard test fixtures", SupportStatus = ModuleSupportStatus.Fixture }
    };

    public static ImmutableArray<ModuleDependency> Empty => [];
}
