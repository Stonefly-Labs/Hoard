using Hoard.Fixtures.Artifacts.Local;
using Hoard.Hosting;

namespace Hoard.Fixtures.Artifacts.BoundaryLeak;

public sealed class LeakingArtifactContract
{
    public LocalArtifactStore? Provider { get; init; }
    public HoardModuleRegistration? Hosting { get; init; }
}
