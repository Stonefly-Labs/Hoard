using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactCapabilityAssertions
{
    public static async Task MissingGuaranteeAsync(
        IArtifactStoreLifetime lifetime, ArtifactInitialization initialization, string gap,
        Func<bool> rootExists, Func<bool> ready, CancellationToken cancellationToken)
    {
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await lifetime.InitializeAsync(
                initialization, new(), cancellationToken));
            Assert.Equal(gap == "authority" ? ArtifactFailureCode.Denied : ArtifactFailureCode.Unsupported, failed.Code);
            Assert.False(rootExists());
            Assert.False(ready());
        }
        finally
        {
            var stopped = Success(await lifetime.StopAsync(new(), cancellationToken));
            Assert.Equal(ArtifactCleanupState.Released, stopped.State);
        }
    }

    public static async Task CompleteProfileAsync(
        IArtifactStoreLifetime lifetime, ArtifactStoreIdentity identity, IArtifactCoordinationAuthority authority,
        Func<bool> ready, CancellationToken cancellationToken)
    {
        var limits = new ArtifactLimits(artifactBytes: 1024, stagingBytes: 2048, transferSlots: 1, waitingCalls: 0);
        try
        {
            var admission = Success(await lifetime.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), cancellationToken));
            Assert.True(admission.Capabilities.MeetsBaseline);
            Assert.Equal(limits, admission.Capabilities.Limits);
            Assert.False(admission.Capabilities.RangeReads);
            Assert.True(admission.Capabilities.Sha512);
            Assert.True(ready());
        }
        finally { Assert.Equal(ArtifactCleanupState.Released, Success(await lifetime.StopAsync(new(), cancellationToken)).State); }
        Assert.False(ready());
    }
}
