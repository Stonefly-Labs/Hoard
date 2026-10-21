using System.Text.Json;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationDistributionTests
{
    [Fact]
    public void Missing_distribution_inputs_cannot_pass_as_empty_package_proof()
    {
        Assert.Throws<InvalidOperationException>(() => Verify("{}"));
        Assert.Throws<InvalidOperationException>(() => Verify("""{"journeys":[],"oldBinaries":[]}"""));
    }

    [Fact]
    public void Prepared_configuration_distributions_and_old_binaries_are_complete()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_CONFIGURATION_EVIDENCE");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-configuration.sh to prepare actual distribution evidence.");
        Verify(File.ReadAllText(path!));
    }

    private static void Verify(string text)
    {
        using var document = JsonDocument.Parse(text);
        var root = document.RootElement;
        if (!root.TryGetProperty("journeys", out var journeys) || journeys.GetArrayLength() != 9
            || journeys.EnumerateArray().Any(j => !j.GetProperty("passed").GetBoolean() || j.GetProperty("events").GetInt32() <= 0)
            || !root.TryGetProperty("oldBinaries", out var binaries) || binaries.GetArrayLength() != 2)
        { throw new InvalidOperationException("Missing configuration distribution proof."); }
        foreach (var entry in binaries.EnumerateArray())
        {
            var bytes = File.ReadAllBytes(entry.GetProperty("assembly").GetString()!);
            var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
            Assert.Equal(entry.GetProperty("sha256").GetString(), hash);
        }
    }
}
