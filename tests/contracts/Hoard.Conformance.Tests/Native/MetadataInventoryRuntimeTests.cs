namespace Hoard.Conformance.Tests;

public sealed class MetadataInventoryRuntimeTests
{
    [Fact]
    public void Sqlite_current_input_inventory_preserves_named_assertion_and_same_source_repair()
        => Verify(nameof(Sqlite_current_input_inventory_preserves_named_assertion_and_same_source_repair));

    [Fact]
    public void Memory_current_input_inventory_preserves_named_assertion_and_same_source_repair()
        => Verify(nameof(Memory_current_input_inventory_preserves_named_assertion_and_same_source_repair));

    private static void Verify(string method)
        => MetadataInventorySource.Verify(
            Environment.GetEnvironmentVariable("HOARD_METADATA_INVENTORY_CONTEXT")
                ?? throw new InvalidOperationException("Actual metadata inventory source context is required."),
            typeof(MetadataInventoryRuntimeTests).FullName + "." + method);
}
