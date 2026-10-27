#if CONFORMANCE_PROVIDER_PACKAGES
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
#endif

namespace Hoard.Fixtures.Conformance.Host;

public static class OwnershipFixtures
{
    public sealed class ControlledCallback(bool cooperative, bool failAfterRelease = false)
    {
        private readonly TaskCompletionSource entered = CompositionFixtures.Barrier();
        private readonly TaskCompletionSource release = CompositionFixtures.Barrier();
        private readonly TaskCompletionSource settled = CompositionFixtures.Barrier();

        public Task Entered => entered.Task;
        public Task Settled => settled.Task;
        public Task? Work { get; private set; }
        public void Release() => release.TrySetResult();

        public Task RunAsync() => RunAsync(CancellationToken.None);
        public Task RunAsync(CancellationToken cancellationToken) => Work = RunCoreAsync(cancellationToken);

        private async Task RunCoreAsync(CancellationToken cancellationToken)
        {
            entered.TrySetResult();
            try
            {
                if (cooperative) { await release.Task.WaitAsync(cancellationToken); }
                else { await release.Task; }
                if (failAfterRelease)
                {
                    throw new InvalidOperationException(
                        "credential=conformance-secret; https://unsafe.example/token; /private/conformance",
                        new Exception("seeded-secret"));
                }
            }
            finally { settled.TrySetResult(); }
        }
    }

#if CONFORMANCE_PROVIDER_PACKAGES
    public sealed class ControlledAdmission
    {
        private readonly ArtifactStoreIdentity identity;
        private readonly ArtifactCoordinationAuthority authority;

        public ControlledAdmission(string root, string variant, bool repaired)
        {
            if (variant is not ("authority-identity" or "mandatory-guarantee"))
            { throw new ArgumentOutOfRangeException(nameof(variant)); }
            identity = new("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
            var authorityIdentity = variant == "authority-identity" && !repaired
                ? new ArtifactStoreIdentity(identity.ProviderModuleId, identity.InstanceId, Guid.NewGuid()) : identity;
            authority = new(authorityIdentity);
            if (variant == "mandatory-guarantee" && !repaired)
            {
                Controls.CapabilitiesForAdmission = capabilities => new(1, capabilities.Durability,
                    capabilities.Enumeration, capabilities.Limits, boundedStreaming: false);
            }
            Store = new(root, controls: Controls);
        }

        public LocalFaultControls Controls { get; } = new();
        public LocalArtifactStore Store { get; }
        public ArtifactResult<ArtifactAdmission>? Admission { get; private set; }
        public ArtifactResult<ArtifactShutdown>? Shutdown { get; private set; }

        public async Task InitializeAsync(CancellationToken cancellationToken)
        {
            Admission = await Store.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, authority), new(), cancellationToken);
            if (Admission is not ArtifactResult<ArtifactAdmission>.Success)
            { throw new InvalidOperationException("Selected store admission failed."); }
        }

        public async Task StopAsync(CancellationToken cancellationToken)
            => Shutdown = await Store.StopAsync(new(), cancellationToken);
    }
#endif
}
