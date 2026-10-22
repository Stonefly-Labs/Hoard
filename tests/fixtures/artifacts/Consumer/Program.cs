using System.Text.Json;
using Hoard.Fixtures.Artifacts.Consumer;
using Hoard.Fixtures.Artifacts.HostAdapters;

if (args.Length != 2 || args[0] is not ("local" or "object"))
{
    Console.Error.WriteLine("Artifact consumer requires an explicit fixture and private root.");
    return 2;
}
await using var session = await ArtifactFixtureSession.CreateForQualificationAsync(args[0], args[1]);
var result = await ArtifactConsumer.RoundTripAsync(session.Store, session.Validator, session.Authority, session.Identity);
Console.WriteLine(JsonSerializer.Serialize(new { qualification = false, provider = args[0], roundTrip = result }));
return 0;
