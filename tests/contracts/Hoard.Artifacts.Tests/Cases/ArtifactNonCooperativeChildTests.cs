using System.Diagnostics;
using System.Text.Json;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactNonCooperativeChildTests
{
    [Theory]
    [InlineData("local", "source")]
    [InlineData("local", "destination")]
    [InlineData("local", "native")]
    [InlineData("object", "source")]
    [InlineData("object", "destination")]
    [InlineData("object", "native")]
    public async Task Owned_child_retains_noncooperative_work_until_parent_termination(string provider, string scenario)
    {
        using var root = new ArtifactTestRoot();
        var run = Guid.NewGuid().ToString();
        var binary = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CRASH_RUNNER")
            ?? throw new InvalidOperationException("Artifact child runner is required.");
        var start = new ProcessStartInfo("dotnet")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            RedirectStandardInput = true
        };
        foreach (var argument in new[] { binary, "noncooperative", root.Path, provider, scenario, run })
        { start.ArgumentList.Add(argument); }
        using var child = Process.Start(start) ?? throw new InvalidOperationException("Artifact owned child did not start.");
        root.AllowCleanup = false;
        var errors = ArtifactChildOutput.ReadToEndAsync(child.StandardError);
        var proofs = new List<JsonElement>();
        try
        {
            await ReadProofAsync("contained");
            await child.StandardInput.WriteLineAsync("inspect");
            await child.StandardInput.FlushAsync();
            await ReadProofAsync("inspected");
            Assert.False(child.HasExited);
            child.Kill();
            await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));
            Assert.NotEqual(0, child.ExitCode);
            Assert.Empty(await errors);
            var capture = System.IO.Path.GetFullPath(Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CRASH_PROOFS")
                ?? throw new InvalidOperationException("Artifact child proof directory is required."));
            Directory.CreateDirectory(capture);
            File.WriteAllText(System.IO.Path.Combine(capture, $"noncooperative-{provider}-{scenario}.json"),
                JsonSerializer.Serialize(new
                {
                    qualification = false,
                    durableCrashProof = false,
                    provider,
                    scenario,
                    runId = run,
                    parentPid = Environment.ProcessId,
                    killedPid = child.Id,
                    killedExitCode = child.ExitCode,
                    observations = proofs
                }));
        }
        finally
        {
            if (!child.HasExited) { child.Kill(); await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10)); }
            root.AllowCleanup = child.HasExited;
        }

        async Task ReadProofAsync(string phase)
        {
            var line = await ArtifactChildOutput.ReadLineAsync(child.StandardOutput);
            Assert.NotNull(line);
            Assert.InRange(line.Length, 1, 16384);
            using var document = JsonDocument.Parse(line);
            var proof = document.RootElement;
            Assert.Equal("noncooperative", proof.GetProperty("eventName").GetString());
            Assert.Equal(phase, proof.GetProperty("phase").GetString());
            Assert.Equal(child.Id, proof.GetProperty("pid").GetInt32());
            Assert.Equal(run, proof.GetProperty("runId").GetString());
            Assert.Equal(provider, proof.GetProperty("provider").GetString());
            Assert.Equal(scenario, proof.GetProperty("scenario").GetString());
            Assert.False(proof.GetProperty("durableCrashProof").GetBoolean());
            Assert.Equal("RetainedLiveOwnership", proof.GetProperty("cleanup").GetString());
            var callerCode = proof.GetProperty("callerCode").GetString();
            if (scenario == "native") { Assert.True(callerCode is "Uncertain" or "DeadlineExceeded"); }
            else { Assert.Equal("CancelledBeforeCommit", callerCode); }
            Assert.Equal("CleanupIncomplete", proof.GetProperty("admissionCode").GetString());
            Assert.Equal("CleanupIncomplete", proof.GetProperty("shutdownCode").GetString());
            Assert.Equal(1, proof.GetProperty("enteredWorkers").GetInt32());
            foreach (var check in new[] { "workerPending", "borrowedStreamsIntact", "rootStillOwned", "readinessBlocked" })
            { Assert.True(proof.GetProperty(check).GetBoolean()); }
            if (scenario is "destination" or "native")
            { Assert.True(proof.GetProperty("protectionRetained").GetBoolean()); }
            proofs.Add(proof.Clone());
        }
    }
}
