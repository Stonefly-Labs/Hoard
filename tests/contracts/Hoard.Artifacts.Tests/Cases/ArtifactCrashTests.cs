using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactCrashTests
{
    [Theory]
    [InlineData("B0")]
    [InlineData("B1")]
    [InlineData("B2")]
    [InlineData("B3")]
    [InlineData("D0")]
    [InlineData("D1")]
    public async Task Real_parent_kill_and_fresh_process_reopen_preserve_exact_receipts_and_control_bytes(string barrier)
    {
        using var root = new ArtifactTestRoot();
        using var control = new ArtifactTestRoot();
        Directory.CreateDirectory(control.Path);
        var state = System.IO.Path.Combine(control.Path, "state.json");
        var run = Guid.NewGuid().ToString();
        var capture = System.IO.Path.GetFullPath(Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CRASH_PROOFS")
            ?? throw new InvalidOperationException("Artifact crash proof directory is required."));
        Directory.CreateDirectory(capture);
        string? barrierProof = null;
        var killedExit = 0;
        var killedPid = 0;
        using (var child = Start("crash"))
        {
            root.AllowCleanup = false;
            control.AllowCleanup = false;
            var errors = child.StandardError.ReadToEndAsync();
            try
            {
                var line = await child.StandardOutput.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(60));
                Assert.NotNull(line);
                Assert.InRange(line.Length, 1, 16384);
                using var document = JsonDocument.Parse(line);
                var observed = document.RootElement;
                Assert.Equal("barrier", observed.GetProperty("eventName").GetString());
                Assert.Equal(child.Id, observed.GetProperty("pid").GetInt32());
                Assert.Equal(barrier, observed.GetProperty("barrier").GetString());
                Assert.Equal(run, observed.GetProperty("runId").GetString());
                Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(state))),
                    observed.GetProperty("stateSha256").GetString());
                Assert.Equal(barrier == "B3", observed.GetProperty("acknowledged").GetBoolean());
                barrierProof = line;
                File.Copy(state, System.IO.Path.Combine(capture, barrier + "-state.json"), overwrite: false);
                killedPid = child.Id;
                child.Kill();
                await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));
                Assert.NotEqual(0, child.ExitCode);
                killedExit = child.ExitCode;
                Assert.Empty(await errors);
            }
            finally
            {
                if (!child.HasExited) { child.Kill(); await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10)); }
                root.AllowCleanup = control.AllowCleanup = child.HasExited;
            }
        }
        using var reopened = Start("recover");
        root.AllowCleanup = control.AllowCleanup = false;
        var output = reopened.StandardOutput.ReadToEndAsync();
        var recoveryErrors = reopened.StandardError.ReadToEndAsync();
        try
        {
            await reopened.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(60));
            var errors = await recoveryErrors;
            File.WriteAllText(System.IO.Path.Combine(capture, barrier + "-recovery-errors.txt"), errors);
            Assert.True(errors.Length == 0, errors);
            Assert.Equal(0, reopened.ExitCode);
            Assert.NotEqual(killedPid, reopened.Id);
            var text = await output;
            using var document = JsonDocument.Parse(text);
            var proof = document.RootElement;
            Assert.Equal("recovered", proof.GetProperty("eventName").GetString());
            Assert.Equal(reopened.Id, proof.GetProperty("pid").GetInt32());
            Assert.Equal(run, proof.GetProperty("runId").GetString());
            Assert.Equal(barrier, proof.GetProperty("barrier").GetString());
            foreach (var check in new[] { "controlReadback", "controlReceipt", "exactReceipt", "contentReadback" })
            { Assert.True(proof.GetProperty(check).GetBoolean()); }
            if (barrier is "B0" or "B1" or "D0" or "D1") { Assert.True(proof.GetProperty("ownerFenced").GetBoolean()); }
            File.WriteAllText(System.IO.Path.Combine(capture, barrier + ".json"), JsonSerializer.Serialize(new
            {
                provider = "local",
                qualification = false,
                runId = run,
                barrier,
                signal = 9,
                parentPid = Environment.ProcessId,
                killedPid,
                killedExitCode = killedExit,
                recoveredPid = reopened.Id,
                reopenedExitCode = reopened.ExitCode,
                barrierProof = JsonSerializer.Deserialize<JsonElement>(barrierProof!),
                recovery = proof.Clone()
            }));
        }
        finally
        {
            if (!reopened.HasExited) { reopened.Kill(); await reopened.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10)); }
            root.AllowCleanup = control.AllowCleanup = reopened.HasExited;
        }

        Process Start(string mode)
        {
            var binary = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CRASH_RUNNER")
                ?? throw new InvalidOperationException("Artifact crash runner is required.");
            var start = new ProcessStartInfo("dotnet") { RedirectStandardOutput = true, RedirectStandardError = true };
            foreach (var argument in new[] { binary, mode, root.Path, state, barrier, run }) { start.ArgumentList.Add(argument); }
            return Process.Start(start) ?? throw new InvalidOperationException("Artifact owned crash child did not start.");
        }
    }
}
