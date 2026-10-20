using Hoard.Fixtures.Artifact.One;
using Hoard.Fixtures.Identity;
using Hoard.Fixtures.Metadata;
using Hoard.Fixtures.Protocol;
using Hoard.Hosting;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHoard()
    .AddModule<ProtocolProvider>(ProtocolProvider.Declaration)
    .AddModule<MetadataProvider>(MetadataProvider.Declaration)
    .AddModule<ArtifactOneProvider>(ArtifactOneProvider.Declaration)
    .AddModule<IdentityProvider>(IdentityProvider.Declaration);
