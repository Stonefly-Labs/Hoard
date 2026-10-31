using Hoard.Fixtures.Metadata.Consumer;
using Hoard.Fixtures.Metadata.Hosting;

var safeEvents = Environment.GetEnvironmentVariable("HOARD_CONFORMANCE_SAFE_EVENTS") switch
{
    null => false,
    "1" => true,
    _ => throw new ArgumentException("Invalid consumer event mode.")
};
if (safeEvents && (args.Length != 2 || args[0] is not ("sqlite" or "memory") || !Path.IsPathFullyQualified(args[1])))
{ throw new ArgumentException("Expected explicit provider and owned database arguments."); }
await using var fixture = safeEvents
    ? MetadataFixtureSession.Create(args[0], TimeProvider.System, args[1])
    : MetadataFixtureSession.CreateFromEnvironment(TimeProvider.System);
await MetadataConsumer.ExecuteAsync(fixture.Store, fixture.Schema);
Console.WriteLine(safeEvents ? "{\"event\":\"test\",\"code\":\"None\",\"value\":1}" : "metadata-package-consumer-compatible");
