using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

internal sealed record ObjectState(int Format, string Module, Guid Instance, Guid Epoch, Guid Process,
    DateTimeOffset Created, ArtifactLimits Limits);
