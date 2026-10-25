using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed partial class ArtifactContractTests(ITestOutputHelper output)
{
    partial void ObserveContract(string method, Type contract) => ConformanceOriginalObservationOutput.WriteIfRequested(output,
        "Hoard.Artifacts.Tests.ArtifactContractTests." + method,
        null, "loaded-contract", ("contract", contract));
}
