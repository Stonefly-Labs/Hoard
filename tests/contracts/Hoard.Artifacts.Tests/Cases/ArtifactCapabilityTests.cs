using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactCapabilityTests
{
    [Theory]
    [InlineData("local", "version")]
    [InlineData("local", "publication")]
    [InlineData("local", "deletion")]
    [InlineData("local", "recovery")]
    [InlineData("local", "fencing")]
    [InlineData("local", "readers")]
    [InlineData("local", "streaming")]
    [InlineData("local", "authority")]
    [InlineData("object", "version")]
    [InlineData("object", "publication")]
    [InlineData("object", "deletion")]
    [InlineData("object", "recovery")]
    [InlineData("object", "fencing")]
    [InlineData("object", "readers")]
    [InlineData("object", "streaming")]
    [InlineData("object", "authority")]
    public async Task Missing_mandatory_guarantees_versions_or_authority_reject_before_io(string provider, string gap)
    {
        using var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var scope = gap == "authority"
            ? new ArtifactStoreIdentity(identity.ProviderModuleId, Guid.NewGuid(), Guid.NewGuid()) : identity;
        var authority = new ArtifactCoordinationAuthority(scope);
        ArtifactCapabilities Inject(ArtifactCapabilities value) => new(
            gap == "version" ? 2 : 1, value.Durability, value.Enumeration, value.Limits,
            conditionalPublication: gap != "publication", conditionalDeletion: gap != "deletion",
            stagingRecovery: gap != "recovery", ownerFencing: gap != "fencing",
            readerProtection: gap != "readers", boundedStreaming: gap != "streaming");
        IArtifactStoreLifetime lifetime = provider == "local"
            ? new LocalArtifactStore(root.Path, controls: new() { CapabilitiesForAdmission = Inject })
            : new ObjectArtifactStore(root.Path, controls: new() { CapabilitiesForAdmission = Inject });
        await ArtifactCapabilityAssertions.MissingGuaranteeAsync(lifetime,
            new(ArtifactInitializationMode.CreateEmpty, identity, authority), gap,
            () => Directory.Exists(root.Path), () => Ready(lifetime), default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Complete_capability_profile_accepts_configured_limits_and_keeps_ranges_optional(string provider)
    {
        using var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity);
        ArtifactCapabilities Complete(ArtifactCapabilities value) => new(1, value.Durability, value.Enumeration, value.Limits);
        IArtifactStoreLifetime lifetime = provider == "local"
            ? new LocalArtifactStore(root.Path, controls: new() { CapabilitiesForAdmission = Complete })
            : new ObjectArtifactStore(root.Path, controls: new() { CapabilitiesForAdmission = Complete });
        await ArtifactCapabilityAssertions.CompleteProfileAsync(lifetime, identity, authority, () => Ready(lifetime), default);
    }

    private static bool Ready(IArtifactStoreLifetime lifetime) => lifetime switch
    {
        LocalArtifactStore local => local.Ready,
        ObjectArtifactStore objects => objects.Ready,
        _ => throw new InvalidOperationException("Unknown artifact fixture.")
    };
}
