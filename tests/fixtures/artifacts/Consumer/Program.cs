using System.Text.Json;
using Hoard.Fixtures.Artifacts.Consumer;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Abstractions.Storage;

if (args.Length == 2 && args[0] == "qualification")
{
    Console.WriteLine(QualificationReport.Materialize(args[1]));
    return 0;
}
if (args.Length != 2 || args[0] is not ("local" or "object"))
{
    Console.Error.WriteLine("Artifact consumer requires an explicit fixture and private root.");
    return 2;
}
await using var session = await ArtifactFixtureSession.CreateForQualificationAsync(args[0], args[1],
    references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
var operations = await ArtifactConsumer.CommonJourneyAsync(
    session.Store, session.Validator, session.Maintenance, session.Authority, session.Identity);
if (Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CONTEXT_PATH") is { Length: > 0 } context)
{
    File.WriteAllText(context, JsonSerializer.Serialize(new
    {
        implementationId = session.Identity.ProviderModuleId,
        runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
        capabilities = session.Capabilities,
        configuration = new
        {
            initialization = "CreateEmpty",
            limits = session.Capabilities.Limits,
            control = new ArtifactCallOptions(),
            transfer = new ArtifactTransferOptions(),
            cleanup = new ArtifactCleanupOptions(),
            maintenance = new ArtifactMaintenanceOptions(),
            ownership = new ArtifactOwnershipOptions()
        }
    }));
}
Console.WriteLine(JsonSerializer.Serialize(new { qualification = false, provider = args[0], roundTrip = true, operations }));
return 0;
