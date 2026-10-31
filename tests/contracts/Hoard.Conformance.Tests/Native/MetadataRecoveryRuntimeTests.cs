namespace Hoard.Conformance.Tests;

public sealed class MetadataRecoveryRuntimeTests
{
    [Fact]
    public void Complete_current_input_native_recovery_graph_preserves_all_barriers_and_readbacks()
    {
        var context = Environment.GetEnvironmentVariable("HOARD_METADATA_RECOVERY_CONTEXT")
            ?? throw new InvalidOperationException("Actual metadata recovery source context is required.");
        MetadataRecoverySource.Verify(context);
    }
}
