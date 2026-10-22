using Hoard.Fixtures.Metadata.Consumer;
using Hoard.Fixtures.Metadata.Hosting;

await using var fixture = MetadataFixtureSession.CreateFromEnvironment(TimeProvider.System);
await MetadataConsumer.ExecuteAsync(fixture.Store, fixture.Schema);
Console.WriteLine("metadata-package-consumer-compatible");
