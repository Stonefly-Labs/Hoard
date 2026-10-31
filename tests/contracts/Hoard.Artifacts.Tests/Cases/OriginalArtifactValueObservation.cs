using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed partial class ArtifactValueTests(ITestOutputHelper output)
{
    partial void ObserveContract(string method, Type contract) => ConformanceOriginalObservationOutput.WriteIfRequested(output,
        "Hoard.Artifacts.Tests.ArtifactValueTests." + method,
        null, "loaded-contract", ("contract", contract));
}
