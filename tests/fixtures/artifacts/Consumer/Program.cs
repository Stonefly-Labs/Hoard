using System.Text.Json;
using Hoard.Fixtures.Artifacts.Consumer;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Abstractions.Storage;

if (args.Length != 2 || args[0] is not ("local" or "object"))
{
    Console.Error.WriteLine("Artifact consumer requires an explicit fixture and private root.");
    return 2;
}
await using var session = await ArtifactFixtureSession.CreateForQualificationAsync(args[0], args[1],
    references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
var operations = await ArtifactConsumer.CommonJourneyAsync(
    session.Store, session.Validator, session.Maintenance, session.Authority, session.Identity);
Console.WriteLine(JsonSerializer.Serialize(new { qualification = false, provider = args[0], roundTrip = true, operations }));
return 0;
