using Hoard.Fixtures.Artifacts.Local;
using Hoard.Hosting;
using Hoard.Abstractions.Storage;
using NuGet.Versioning;

namespace Hoard.Fixtures.Artifacts.BoundaryLeak;

public sealed class LeakingArtifactContract
{
    public LocalArtifactStore? Provider { get; init; }
    public HoardModuleRegistration? Hosting { get; init; }
    public NuGetVersion? Sdk { get; init; }
    public FileInfo? RawPath { get; init; }
    public FileStream? RawFile { get; init; }
    public IServiceProvider? ServiceLocator { get; init; }
}

public sealed class AllowedArtifactContract
{
    public IArtifactStore? Store { get; init; }
    public Stream? BorrowedStream { get; init; }
    public ArtifactStamp? Stamp { get; init; }
}
