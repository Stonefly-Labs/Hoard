using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore : IArtifactStore, IArtifactEvidenceValidator, IArtifactMaintenance
{
}
