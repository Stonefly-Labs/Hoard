namespace Hoard.Testing.Conformance.Bindings;

public sealed record MetadataFaultCounters(long BoundaryObservations, long InternalFailures, long IncompleteCleanups)
{
    public long BoundaryObservations { get; } = Nonnegative(BoundaryObservations);
    public long InternalFailures { get; } = Nonnegative(InternalFailures);
    public long IncompleteCleanups { get; } = Nonnegative(IncompleteCleanups);

    private static long Nonnegative(long value) => value >= 0 ? value : throw new ArgumentException("BindingInvalid");
}
