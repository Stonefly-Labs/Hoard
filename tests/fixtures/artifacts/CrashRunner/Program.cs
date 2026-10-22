using System.Text.Json;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;

if (args.Length == 5 && args[0] is "crash" or "recover")
{
    return await ArtifactCrashScenario.ExecuteAsync(args);
}
if (args.Length == 5 && args[0] == "noncooperative")
{
    return await ArtifactNonCooperativeScenario.ExecuteAsync(args);
}
if (args.Length == 5 && args[0] == "admission")
{
    var identity = new ArtifactStoreIdentity(args[2], Guid.Parse(args[3]), Guid.Parse(args[4]));
    var store = new LocalArtifactStore(args[1]);
    var result = await store.InitializeAsync(
        new(ArtifactInitializationMode.ReopenCompatible, identity, new ArtifactCoordinationAuthority(identity)), new(), default);
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        pid = Environment.ProcessId,
        admitted = result is ArtifactResult<ArtifactAdmission>.Success,
        code = result is ArtifactResult<ArtifactAdmission>.Failure failure ? failure.Code.ToString() : "Admitted"
    }));
    await store.StopAsync(new(), default);
    return 0;
}
Console.Error.WriteLine("Artifact child requires an explicit admission, crash or non-cooperative scenario.");
return 1;
