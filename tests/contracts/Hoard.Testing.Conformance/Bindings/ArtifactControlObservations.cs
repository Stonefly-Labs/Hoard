using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Bindings;

public sealed record ArtifactInitializationObservation(bool RootExists, bool Ready);

public sealed record ArtifactCompetingInitializationObservation(
    ArtifactResult<ArtifactAdmission> Admission, ArtifactResult<ArtifactShutdown> Shutdown);

public interface IArtifactFaultRegistration : IAsyncDisposable
{
    long ObservationCount { get; }
    ValueTask WaitForEntryAsync(CancellationToken cancellationToken);
}

public interface IArtifactSynchronousHold : IArtifactFaultRegistration
{
    void Release();
}
