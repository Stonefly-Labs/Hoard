using System.Collections.Immutable;

namespace Hoard.Hosting.Lifecycle;

public sealed class HoardLifecycleException : Exception
{
    internal HoardLifecycleException(ImmutableArray<HoardLifecycleDiagnostic> diagnostics)
        : base("Hoard lifecycle failed. Inspect safe Diagnostics and correlation identifiers.") => Diagnostics = diagnostics;

    public ImmutableArray<HoardLifecycleDiagnostic> Diagnostics { get; }
}
