using NuGet.Versioning;

namespace Hoard.Foundation.Tests;

internal sealed record ContractChangeExample(
    string Id, string OldVersion, string ProposedVersion, string ConsumerImpact, string ImplementerImpact,
    string BinaryImpact, string BehaviorImpact, string OldRange, string NewRange,
    string Migration, string Qualification, string Rollback)
{
    internal string RequiredTransition => NuGetVersion.Parse(OldVersion).Major == 0 ? "pre-1.0-minor" : "stable-major";
    internal bool ProposedReleaseValid
    {
        get
        {
            var old = NuGetVersion.Parse(OldVersion);
            var proposed = NuGetVersion.Parse(ProposedVersion);
            return old.Major == 0
                ? proposed.Major > 0 || proposed.Minor > old.Minor
                : proposed.Major > old.Major;
        }
    }
}

internal static class ContractChangeExamples
{
    internal static IReadOnlyList<ContractChangeExample> All { get; } =
    [
        new("C-05", "1.3.0", "1.4.0",
            "A caller using only Describe still compiles; that does not establish compatibility.",
            "An existing implementation lacks Required: CS0535 in the required-member fixture.",
            "Old implementer binaries cannot satisfy the expanded required interface agreement.",
            "Implementers must supply the new required operation.",
            "[1.0.0,2.0.0)", "[2.0.0,3.0.0)",
            "Release 2.0.0; implement Required, rebuild providers/hosts, update declarations.",
            "Recompile every supported implementer and rerun category behavior qualification.",
            "Restore the previous host/contract/provider set together; do not relabel old binaries."),
        new("C-06", "0.1.3", "0.1.4",
            "An unchanged caller may compile; patch compatibility also includes implementers.",
            "Required-member fixture rejects the existing implementation with CS0535.",
            "An expanded interface also changes the binary implementer agreement.",
            "Required operation semantics need explicit qualification.",
            "[0.1.0,0.2.0)", "[0.2.0,0.3.0)",
            "Release 0.2.0, implement the member, rebuild, and replace the narrow compatibility range.",
            "Recompile old implementers against the new contract and test the new obligation.",
            "Revert to the 0.1 host/contract/provider set; never assume all 0.x versions interoperate."),
        new("C-16", "1.4.0", "1.5.0",
            "Source signatures remain identical.",
            "Existing implementations may violate the newly strengthened commit visibility requirement.",
            "Binary shape is unchanged; binary loading is not behavioral proof.",
            "Tightened atomic commit visibility is a breaking observable obligation.",
            "[1.0.0,2.0.0)", "[2.0.0,3.0.0)",
            "Release 2.0.0 with publication behavior migration notes and requalified provider declarations.",
            "Prove visibility under interrupted/corrupt writes; this written example is not store conformance.",
            "Restore the previous qualified composition and documented data/backup strategy before rollback."),
        new("C-17", "1.4.0", "1.4.1",
            "A revised consumer can compile without calling the removed member.",
            "Provider authors must migrate call sites and rebuild supported binaries.",
            "The old compiled caller fails with MissingMethodException after member removal.",
            "The formerly promised operation is absent; a new compilation is not old-binary compatibility.",
            "[1.0.0,2.0.0)", "[2.0.0,3.0.0)",
            "Release 2.0.0; replace removed calls, rebuild consumers/providers and update host/contract ranges.",
            "Run the compiled-old/new-contract fixture and requalify source and behavior separately.",
            "Restore the previous contract DLL with its matching binaries; do not silently substitute a provider.")
    ];
}
