using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;

namespace Hoard.Conformance.Tests;

internal static class SourceImageProvenance
{
    internal static void Verify(
        Stream image, Stream pdb, Action<MetadataReader, MetadataReader> verifyDocuments)
    {
        using var pe = new PEReader(image, PEStreamOptions.LeaveOpen);
        Assert.True(pe.HasMetadata);
        var entry = Assert.Single(pe.ReadDebugDirectory(), value => value.Type == DebugDirectoryEntryType.CodeView);
        var codeView = pe.ReadCodeViewDebugDirectoryData(entry);
        using var provider = MetadataReaderProvider.FromPortablePdbStream(pdb, MetadataStreamOptions.LeaveOpen);
        var reader = provider.GetMetadataReader();
        var header = reader.DebugMetadataHeader ?? throw new InvalidOperationException("ProofMismatch");
        var content = new BlobContentId(header.Id);
        Assert.Equal(codeView.Guid, content.Guid);
        Assert.Equal(entry.Stamp, content.Stamp);
        verifyDocuments(pe.GetMetadataReader(), reader);
    }
}
