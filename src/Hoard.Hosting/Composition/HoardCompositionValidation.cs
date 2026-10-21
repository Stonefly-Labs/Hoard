using System.Collections.Immutable;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Composition;

public sealed class HoardCompositionValidation
{
    internal HoardCompositionValidation(HoardValidatedComposition? composition,
        ImmutableArray<HoardLifecycleDiagnostic> diagnostics, int omittedCount)
    {
        Composition = composition;
        Diagnostics = diagnostics;
        OmittedCount = omittedCount;
    }

    public HoardValidatedComposition? Composition { get; }
    public ImmutableArray<HoardLifecycleDiagnostic> Diagnostics { get; }
    public int OmittedCount { get; }
}
