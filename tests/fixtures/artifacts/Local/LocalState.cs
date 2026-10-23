using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

internal sealed record LocalState(int Format, string ProviderId, Guid InstanceId, Guid Epoch,
    Guid SessionId, DateTimeOffset TimeFloor, ArtifactLimits Limits);
internal sealed record LocalEnvelope(string Payload, string Sha256);
