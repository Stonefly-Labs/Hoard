using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Configuration.Conversion;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationConversionTests
{
    internal static string Fixture()
    {
        var current = JsonNode.Parse(ConfigurationSecretTests.Document())!.AsObject();
        var old = new JsonObject { ["configurationversion"] = "fixture-v0" };
        foreach (var pair in new[] { ("enabledmodules", "enabled"), ("metadatamodule", "metadata"),
            ("artifactmodule", "artifact"), ("identitymodules", "identities"),
            ("requiredcapabilities", "capabilities"), ("modules", "providers") })
        { old[pair.Item2] = current[pair.Item1]!.DeepClone(); }
        return old.ToJsonString();
    }

    [Fact]
    public async Task Preview_is_secret_free_and_approved_apply_preserves_original_references_without_activation()
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var original = Fixture();
        var source = harness.File("old.json", original);
        var destination = source + ".converted";
        var reads = 0;
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) =>
            { reads++; return ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential); });
        Assert.Equal(HoardConfigurationOutcome.Validated, preview.Outcome);
        Assert.Equal(0, reads);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.NotEmpty(preview.Changes);
        var safe = JsonSerializer.Serialize(preview) + preview;
        foreach (var payload in new[] { source, destination, ConfigurationTestHarness.Credential, ConfigurationTestHarness.Locator })
        { Assert.DoesNotContain(payload, safe); }
        preview.Session!.Approve();
        await using var applied = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(HoardConfigurationApplyOutcome.Published, applied.Outcome);
        Assert.Equal(1, reads);
        Assert.Equal(original, File.ReadAllText(source));
        using var converted = JsonDocument.Parse(File.ReadAllText(destination));
        Assert.Equal(1, converted.RootElement.GetProperty("configurationversion").GetInt32());
        Assert.Equal(ConfigurationTestHarness.Locator, converted.RootElement.GetProperty("modules").GetProperty("metadata")
            .GetProperty("options").GetProperty("credential").GetProperty("target").GetString());
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, File.ReadAllText(destination));
        Assert.Empty(LifecycleFixtures.Controls);
        await using var reused = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(HoardConfigurationApplyOutcome.Rejected, reused.Outcome);
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("unknown")]
    [InlineData("version")]
    [InlineData("option-version")]
    [InlineData("yaml")]
    public async Task Unsupported_or_incomplete_synthetic_input_is_not_guessed(string defect)
    {
        await using var harness = new ConfigurationTestHarness();
        var root = JsonNode.Parse(Fixture())!;
        if (defect == "missing") { root.AsObject().Remove("identities"); }
        if (defect == "unknown") { root["private-setting"] = true; }
        if (defect == "version") { root["configurationversion"] = "released-version-never-supported"; }
        if (defect == "option-version") { root["providers"]!["metadata"]!["optionsversion"] = 99; }
        var source = harness.File("old.json", defect == "yaml" ? "version: fixture-v0" : root.ToJsonString());
        var original = File.ReadAllBytes(source);
        await using var preview = await ConfiguredFixtures.Registry().PreviewConfigurationConversionAsync(
            source, source + ".new", LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, preview.Outcome);
        Assert.Null(preview.Session);
        Assert.Equal(original, File.ReadAllBytes(source));
        Assert.False(File.Exists(source + ".new"));
    }

    [Theory]
    [InlineData("unapproved")]
    [InlineData("disposed")]
    [InlineData("source")]
    [InlineData("builder")]
    [InlineData("secret")]
    [InlineData("destination")]
    public async Task Approval_pins_exact_context_and_full_validation_precedes_publication(string defect)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var destination = source + ".new";
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) =>
                ValueTask.FromResult<string?>(defect == "secret" ? null : ConfigurationTestHarness.Credential));
        Assert.NotNull(preview.Session);
        if (defect != "unapproved") { preview.Session.Approve(); }
        if (defect == "disposed") { await preview.Session.DisposeAsync(); }
        if (defect == "source") { File.AppendAllText(source, " "); }
        if (defect == "builder") { builder.Services.AddSingleton(new object()); }
        if (defect == "destination") { File.WriteAllText(destination, "existing"); }
        await using var applied = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(HoardConfigurationApplyOutcome.Rejected, applied.Outcome);
        Assert.Empty(LifecycleFixtures.Controls);
        if (defect == "destination") { Assert.Equal("existing", File.ReadAllText(destination)); }
        else { Assert.False(File.Exists(destination)); }
    }

    [Theory]
    [InlineData("Staged")]
    [InlineData("Write")]
    [InlineData("Flush")]
    [InlineData("Closed")]
    [InlineData("PrePublish")]
    [InlineData("Published")]
    public async Task Real_publication_faults_preserve_original_and_report_actual_commit(string stageName)
    {
        var stage = Enum.Parse<ConfigurationPublicationStage>(stageName);
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var original = File.ReadAllBytes(source);
        var destination = source + ".new";
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
        preview.Session!.PublicationObserver = at =>
        {
            if (at == stage) { throw new IOException(ConfigurationTestHarness.Credential); }
        };
        preview.Session.Approve();
        await using var applied = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(stage == ConfigurationPublicationStage.Published ? HoardConfigurationApplyOutcome.Published
            : HoardConfigurationApplyOutcome.Rejected, applied.Outcome);
        Assert.Equal(original, File.ReadAllBytes(source));
        Assert.Equal(stage == ConfigurationPublicationStage.Published, File.Exists(destination));
        Assert.Empty(Directory.GetFiles(Path.GetDirectoryName(source)!, ".hoard-configuration-*.tmp"));
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(applied));
    }

    [Fact]
    public async Task Racing_existing_destination_is_never_clobbered()
    {
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var destination = source + ".new";
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
        preview.Session!.PublicationObserver = stage =>
        {
            if (stage == ConfigurationPublicationStage.PrePublish) { File.WriteAllText(destination, "racing-writer"); }
        };
        preview.Session.Approve();
        await using var result = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(HoardConfigurationApplyOutcome.Rejected, result.Outcome);
        Assert.Equal("racing-writer", File.ReadAllText(destination));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Timed_out_dispatched_publication_is_pending_until_actual_nonpublication_is_observed(bool cancel)
    {
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        var source = harness.File("old.json", Fixture());
        var destination = source + ".new";
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), new() { TimeProvider = clock, OperationTimeoutMilliseconds = 50 },
            readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
        preview.Session!.PublicationObserver = stage =>
        {
            if (stage == ConfigurationPublicationStage.PrePublish)
            { entered.TrySetResult(); release.Task.GetAwaiter().GetResult(); }
        };
        preview.Session.Approve();
        using var cancellation = new CancellationTokenSource();
        var apply = builder.ApplyConfigurationConversionAsync(preview.Session, cancellation.Token);
        harness.Observe(apply);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(50));
            if (cancel) { cancellation.Cancel(); }
            else { clock.Advance(TimeSpan.FromMilliseconds(50)); }
            await using var result = await apply.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(HoardConfigurationApplyOutcome.PublicationPending, result.Outcome);
            Assert.Equal(HoardConfigurationPublicationStatus.Pending, result.Publication.Status);
            var frozen = JsonSerializer.Serialize(result.Report);
            await result.DisposeAsync();
            release.TrySetResult();
            await ConfigurationTestHarness.Until(() => result.Supervision.PendingCount == 0);
            Assert.Equal(HoardConfigurationPublicationStatus.NotPublished, result.Publication.Status);
            Assert.Equal(HoardConfigurationApplyOutcome.PublicationPending, result.Outcome);
            Assert.Equal(frozen, JsonSerializer.Serialize(result.Report));
            Assert.False(File.Exists(destination));
        }
        finally { release.TrySetResult(); }
    }

    [Theory]
    [InlineData(99, false)]
    [InlineData(1, true)]
    public async Task Conversion_rejects_unsupported_disabled_option_versions_without_disabled_work(int version, bool supported)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var calls = 0;
        var reads = 0;
        var builder = ConfiguredFixtures.Registry()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol",
                Hoard.Abstractions.Modules.ModuleCategory.Protocol) with
            {
                Configuration = [new() { Key = "credential", Required = true, SecretReference = true, Description = "Fixture" }]
            })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
            .AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(new(1, [new("credential", HoardOptionType.Secret, true)]),
                (_, _) => { calls++; return ValueTask.FromResult(HoardOptionCheckResult.Accepted); });
        var root = JsonNode.Parse(Fixture())!;
        root["providers"]!["protocol"] = JsonNode.Parse(
            """{"optionsversion":99,"options":{"credential":{"kind":"file","target":"/invented/absent"}}}""");
        root["providers"]!["protocol"]!["optionsversion"] = version;
        var source = harness.File("old.json", root.ToJsonString());
        var original = File.ReadAllBytes(source);
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, source + ".new",
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) =>
            { reads++; return ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential); });
        Assert.Equal(supported ? HoardConfigurationOutcome.Validated : HoardConfigurationOutcome.Failed, preview.Outcome);
        Assert.Equal(0, calls);
        Assert.Equal(0, reads);
        if (supported)
        {
            preview.Session!.Approve();
            await using var applied = await builder.ApplyConfigurationConversionAsync(preview.Session);
            Assert.Equal(HoardConfigurationApplyOutcome.Published, applied.Outcome);
            Assert.Equal(1, reads);
        }
        else { Assert.Null(preview.Session); }
        Assert.Equal(0, calls);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.Equal(original, File.ReadAllBytes(source));
        Assert.Equal(supported, File.Exists(source + ".new"));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Committed_publication_remains_published_while_post_commit_work_times_out(bool cancel)
    {
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        var source = harness.File("old.json", Fixture());
        var original = File.ReadAllBytes(source);
        var destination = source + ".new";
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), new() { TimeProvider = clock, OperationTimeoutMilliseconds = 50 },
            readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
        preview.Session!.PublicationObserver = stage =>
        {
            if (stage == ConfigurationPublicationStage.Published)
            { entered.TrySetResult(); release.Task.GetAwaiter().GetResult(); }
        };
        preview.Session.Approve();
        using var cancellation = new CancellationTokenSource();
        var applying = builder.ApplyConfigurationConversionAsync(preview.Session, cancellation.Token);
        harness.Observe(applying);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(50));
            if (cancel) { cancellation.Cancel(); }
            else { clock.Advance(TimeSpan.FromMilliseconds(50)); }
            await using var result = await applying.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(HoardConfigurationApplyOutcome.Published, result.Outcome);
            Assert.Equal(HoardConfigurationPublicationStatus.Published, result.Publication.Status);
            var frozen = JsonSerializer.Serialize(result.Report);
            Assert.Equal(original, File.ReadAllBytes(source));
            using var published = JsonDocument.Parse(File.ReadAllBytes(destination));
            Assert.Equal(1, published.RootElement.GetProperty("configurationversion").GetInt32());
            release.TrySetResult();
            await ConfigurationTestHarness.Until(() => result.Supervision.PendingCount == 0);
            Assert.Equal(HoardConfigurationApplyOutcome.Published, result.Outcome);
            Assert.Equal(frozen, JsonSerializer.Serialize(result.Report));
        }
        finally { release.TrySetResult(); }
    }

    [Theory]
    [InlineData("source")]
    [InlineData("hardlink")]
    [InlineData("symlink")]
    public async Task Actual_source_aliases_are_rejected_without_changing_either_file(string kind)
    {
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var original = File.ReadAllBytes(source);
        var destination = kind == "source" ? Path.Combine(Path.GetDirectoryName(source)!, ".", "old.json") : source + ".alias";
        if (kind == "symlink") { File.CreateSymbolicLink(destination, source); }
        if (kind == "hardlink")
        {
            using var process = Process.Start(new ProcessStartInfo("ln")
            { UseShellExecute = false, ArgumentList = { source, destination } })!;
            try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)); }
            finally { if (!process.HasExited) { process.Kill(); } }
            Assert.Equal(0, process.ExitCode);
        }
        await using var preview = await ConfiguredFixtures.Registry().PreviewConfigurationConversionAsync(
            source, destination, LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, preview.Outcome);
        Assert.Null(preview.Session);
        Assert.Equal(original, File.ReadAllBytes(source));
        Assert.Equal(original, File.ReadAllBytes(destination));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Publication_rejects_nonprivate_or_direct_symlink_parent_without_creating_output(bool symlink)
    {
        if (OperatingSystem.IsWindows())
        { throw new PlatformNotSupportedException("Publication acceptance requires a supported Unix platform."); }
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var parent = Path.Combine(Path.GetDirectoryName(source)!, "output");
        var link = parent + ".link";
        Directory.CreateDirectory(parent);
        File.SetUnixFileMode(parent, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute
            | (symlink ? 0 : UnixFileMode.GroupRead));
        if (symlink) { Directory.CreateSymbolicLink(link, parent); }
        var destination = Path.Combine(symlink ? link : parent, "converted.json");
        try
        {
            var builder = ConfiguredFixtures.Registry();
            await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
                LifecycleFixtures.Versions, new(), readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
            preview.Session!.Approve();
            await using var result = await builder.ApplyConfigurationConversionAsync(preview.Session);
            Assert.Equal(HoardConfigurationApplyOutcome.Rejected, result.Outcome);
            Assert.Equal(HoardConfigurationPublicationStatus.NotPublished, result.Publication.Status);
            Assert.False(File.Exists(destination));
            Assert.Empty(Directory.GetFiles(parent));
        }
        finally
        {
            if (File.Exists(destination)) { File.Delete(destination); }
            if (symlink) { Directory.Delete(link); }
            Directory.Delete(parent);
        }
    }

    [Fact]
    public async Task Cancelled_apply_before_dispatch_reads_no_secret_and_publishes_nothing()
    {
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var destination = source + ".new";
        var reads = 0;
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) =>
            { reads++; return ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential); });
        preview.Session!.Approve();
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await using var result = await builder.ApplyConfigurationConversionAsync(preview.Session, cancellation.Token);
        Assert.Equal(HoardConfigurationApplyOutcome.Cancelled, result.Outcome);
        Assert.Equal(HoardConfigurationPublicationStatus.NotPublished, result.Publication.Status);
        Assert.Equal(0, reads);
        Assert.Equal(0, result.Supervision.PendingCount);
        Assert.False(File.Exists(destination));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Context_changed_after_validation_is_rechecked_before_atomic_publication(bool services)
    {
        await using var harness = new ConfigurationTestHarness();
        var source = harness.File("old.json", Fixture());
        var destination = source + ".new";
        var original = File.ReadAllText(source);
        var builder = ConfiguredFixtures.Registry();
        await using var preview = await builder.PreviewConfigurationConversionAsync(source, destination,
            LifecycleFixtures.Versions, new(), readEnvironment: (_, _) => ValueTask.FromResult<string?>(ConfigurationTestHarness.Credential));
        preview.Session!.PublicationObserver = stage =>
        {
            if (stage != ConfigurationPublicationStage.PrePublish) { return; }
            if (services) { builder.Services.AddSingleton(new object()); }
            else { File.AppendAllText(source, " "); }
        };
        preview.Session.Approve();
        await using var result = await builder.ApplyConfigurationConversionAsync(preview.Session);
        Assert.Equal(HoardConfigurationApplyOutcome.Rejected, result.Outcome);
        Assert.Equal(HoardConfigurationPublicationStatus.NotPublished, result.Publication.Status);
        Assert.False(File.Exists(destination));
        Assert.Equal(services ? original : original + " ", File.ReadAllText(source));
    }
}
