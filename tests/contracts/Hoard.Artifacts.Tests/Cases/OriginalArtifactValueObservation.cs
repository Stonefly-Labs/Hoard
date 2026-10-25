using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed partial class ArtifactValueTests(ITestOutputHelper output)
{
    partial void ObserveIdentityContract() => ConformanceOriginalObservationOutput.WriteIfRequested(output,
        "Hoard.Artifacts.Tests.ArtifactValueTests.Identity_bounds_preserve_empty_and_reject_overflow_negative_or_null",
        null, "loaded-contract", ("contract", typeof(ArtifactIdentity)));
}
