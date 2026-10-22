namespace Hoard.Abstractions.Metadata;

public interface IMetadataSchemaAdministration
{
    ValueTask<MetadataResult<MetadataSchemaInspection>> InspectAsync(
        MetadataAdministrationOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareAsync(
        MetadataSchemaRequest request, MetadataAdministrationOptions options, CancellationToken cancellationToken);
}
