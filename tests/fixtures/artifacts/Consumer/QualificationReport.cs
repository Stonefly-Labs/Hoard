using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Consumer;

internal static class QualificationReport
{
    public static string Materialize(string input)
    {
        if (new FileInfo(input).Length > 1048576) { throw new ArgumentException("Qualification input exceeds its bound."); }
        using var document = JsonDocument.Parse(File.ReadAllText(input));
        var request = document.RootElement;
        var environment = request.GetProperty("environment");
        var capabilities = request.GetProperty("capabilities").Deserialize<ArtifactCapabilities>()
            ?? throw new ArgumentException("Qualification capabilities are required.");
        var results = request.GetProperty("cases").EnumerateArray().Select(value =>
            new ArtifactQualificationCaseResult(value.GetProperty("id").GetString()!,
                value.GetProperty("result").GetString() switch
                {
                    "Passed" => ArtifactQualificationCaseStatus.Passed,
                    "NotApplicable" => ArtifactQualificationCaseStatus.NotApplicable,
                    _ => throw new ArgumentException("Qualification case did not pass.")
                },
                TimeSpan.FromMilliseconds(value.GetProperty("durationMs").GetDouble()),
                [value.GetProperty("sha256").GetString()!])).ToArray();
        var record = new ArtifactQualificationRecord(
            request.GetProperty("implementationId").GetString()!, "0.1.0",
            request.GetProperty("packageSha256").GetString()!,
            request.GetProperty("configurationSha256").GetString()!,
            request.GetProperty("sourceSha256").GetString()!,
            request.GetProperty("lockSha256").GetString()!,
            new ArtifactQualificationEnvironment(
                environment.GetProperty("os").GetString()!, environment.GetProperty("runtime").GetString()!,
                environment.GetProperty("filesystem").GetString()!, environment.GetProperty("flushConfiguration").GetString()!),
            capabilities, results);
        return JsonSerializer.Serialize(record);
    }
}
