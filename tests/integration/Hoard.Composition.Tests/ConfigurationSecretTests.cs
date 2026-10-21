using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationSecretTests
{
    internal static string Document(string kind = "env", string target = ConfigurationTestHarness.Locator)
    {
        var root = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        root["modules"]!["metadata"]!["options"]!["credential"] = new JsonObject { ["kind"] = kind, ["target"] = target };
        return root.ToJsonString();
    }

    [Fact]
    public async Task Secret_is_fixed_owner_only_and_transferred_once_to_existing_lifecycle()
    {
        ConfiguredFixtures.Reset();
        var environment = new Dictionary<string, string> { [ConfigurationTestHarness.Locator] = ConfigurationTestHarness.Credential };
        var phases = new List<HoardOptionCheckPhase>();
        var builder = ConfiguredFixtures.Registry((context, _) =>
        {
            phases.Add(context.Phase);
            Assert.True(context.HasSecretReference("credential"));
            if (context.Phase == HoardOptionCheckPhase.Public) { Assert.False(context.Options.Contains("credential")); }
            else { Assert.Equal(ConfigurationTestHarness.Credential, context.Options.GetSecret("credential").Reveal()); }
            return ValueTask.FromResult(HoardOptionCheckResult.Accepted);
        });
        var input = new HoardConfigurationInput(Document(), environment: environment);
        environment[ConfigurationTestHarness.Locator] = "replacement";
        await using var evaluation = await builder.EvaluateConfigurationAsync(input, LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
        var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        await evaluation.DisposeAsync();
        var secret = ConfiguredFixtures.Delivered!.GetSecret("credential");
        Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
        Assert.Equal(new[] { HoardOptionCheckPhase.Public, HoardOptionCheckPhase.Secrets }, phases);
        Assert.Throws<InvalidOperationException>(() => ConfiguredFixtures.Delivered.GetString("credential"));
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(evaluation) + ConfiguredFixtures.Delivered + secret);
        Assert.DoesNotContain(ConfigurationTestHarness.Locator, JsonSerializer.Serialize(evaluation));
        await lease.DisposeAsync();
        await ConfigurationTestHarness.Until(() =>
        {
            try { secret.Reveal(); return false; }
            catch (ObjectDisposedException) { return true; }
        });
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData(" \t\n")]
    [InlineData("denied")]
    [InlineData("oversize")]
    public async Task Unavailable_environment_secret_has_no_fallback_or_activation(string? value)
    {
        ConfiguredFixtures.Reset();
        var reads = 0;
        var builder = ConfiguredFixtures.Registry();
        await using var result = await builder.EvaluateConfigurationAsync(new(Document(),
            environment: new Dictionary<string, string> { [ConfigurationTestHarness.Locator] = "must-not-fallback" },
            readEnvironment: (_, _) =>
            {
                reads++;
                if (value == "denied") { throw new UnauthorizedAccessException(ConfigurationTestHarness.Credential); }
                return ValueTask.FromResult(value == "oversize" ? new string('s', 65537) : value);
            }), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Contains(result.Report.Diagnostics, d => d.Rule == HoardConfigurationRule.SecretUnavailable);
        Assert.Equal(1, reads);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(result));
    }

    [Theory]
    [InlineData("with edges \n")]
    [InlineData("limit")]
    public async Task Environment_preserves_exact_text_and_accepts_exact_byte_limit(string value)
    {
        var expected = value == "limit" ? new string('s', 65536) : value;
        await using var result = await ConfiguredFixtures.Registry().EvaluateConfigurationAsync(new(Document(),
            environment: new Dictionary<string, string> { [ConfigurationTestHarness.Locator] = expected }),
            LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, result.Outcome);
    }

    [Theory]
    [InlineData("plain")]
    [InlineData("lf")]
    [InlineData("crlf")]
    [InlineData("two-lf")]
    [InlineData("symlink")]
    [InlineData("limit")]
    public async Task Actual_local_file_and_deployment_symlink_preserve_documented_newline_policy(string kind)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var text = kind switch
        {
            "lf" => "credential\n",
            "crlf" => "credential\r\n",
            "two-lf" => "credential\n\n",
            "limit" => new string('s', 65536),
            _ => "credential"
        };
        var path = harness.File("secret", text);
        if (kind == "symlink")
        {
            var link = path + ".link";
            File.CreateSymbolicLink(link, path);
            path = link;
        }
        var builder = ConfiguredFixtures.Registry();
        await using var result = await builder.EvaluateConfigurationAsync(new(Document("file", path)), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, result.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(result.Configuration!);
        var expected = kind == "two-lf" ? "credential\n" : kind == "limit" ? text : "credential";
        Assert.Equal(expected, ConfiguredFixtures.Delivered!.GetSecret("credential").Reveal());
        harness.AssertNoPayload(path);
    }

    [Theory]
    [InlineData("empty")]
    [InlineData("whitespace")]
    [InlineData("bom")]
    [InlineData("nul")]
    [InlineData("utf8")]
    [InlineData("oversize")]
    [InlineData("missing")]
    [InlineData("directory")]
    [InlineData("denied")]
    [InlineData("device")]
    public async Task Invalid_actual_or_denied_mounted_file_is_safe_and_never_constructs(string kind)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var path = harness.File("secret", "credential");
        if (kind == "empty") { File.WriteAllText(path, ""); }
        if (kind == "whitespace") { File.WriteAllText(path, "\r\n\t "); }
        if (kind == "bom") { File.WriteAllBytes(path, [0xef, 0xbb, 0xbf, 65]); }
        if (kind == "nul") { File.WriteAllText(path, "a\0b"); }
        if (kind == "utf8") { File.WriteAllBytes(path, [0xff]); }
        if (kind == "oversize") { File.WriteAllText(path, new string('s', 65537)); }
        if (kind == "missing") { File.Delete(path); }
        if (kind == "directory") { path = Path.GetDirectoryName(path)!; }
        if (kind == "device") { path = OperatingSystem.IsWindows() ? Path.GetDirectoryName(path)! : "/dev/zero"; }
        HoardConfigurationFileReader? reader = kind == "denied"
            ? (_, _) => throw new UnauthorizedAccessException(ConfigurationTestHarness.Credential) : null;
        await using var result = await ConfiguredFixtures.Registry().EvaluateConfigurationAsync(
            new(Document("file", path), readFile: reader), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Empty(LifecycleFixtures.Controls);
        Assert.DoesNotContain(path, JsonSerializer.Serialize(result));
        Assert.DoesNotContain(ConfigurationTestHarness.Credential, JsonSerializer.Serialize(result));
    }

    [Fact]
    public async Task Timed_out_secret_check_retains_input_until_late_fault_and_freezes_result()
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        HoardSecretValue? held = null;
        var builder = ConfiguredFixtures.Registry(async (context, _) =>
        {
            if (context.Phase == HoardOptionCheckPhase.Secrets)
            {
                held = context.Options.GetSecret("credential");
                entered.TrySetResult();
                await release.Task;
                Assert.Equal(ConfigurationTestHarness.Credential, held.Reveal());
                throw new InvalidOperationException(ConfigurationTestHarness.Credential);
            }
            return HoardOptionCheckResult.Accepted;
        });
        var task = builder.EvaluateConfigurationAsync(new(Document(), environment: harness.Environment),
            LifecycleFixtures.Versions, new(), new() { TimeProvider = clock, OperationTimeoutMilliseconds = 50 });
        harness.Observe(task);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(50));
            clock.Advance(TimeSpan.FromMilliseconds(50));
            await using var result = await task.WaitAsync(TimeSpan.FromSeconds(5));
            var frozen = JsonSerializer.Serialize(result.Report);
            await result.DisposeAsync();
            Assert.Equal(ConfigurationTestHarness.Credential, held!.Reveal());
            Assert.Equal(HoardConfigurationOutcome.TimedOut, result.Outcome);
            release.TrySetResult();
            await ConfigurationTestHarness.Until(() => result.Supervision.PendingCount == 0);
            Assert.Throws<ObjectDisposedException>(() => held.Reveal());
            Assert.Single(result.Supervision.Diagnostics.Where(d => d.Rule == HoardConfigurationRule.LateCheckFailure));
            Assert.Equal(frozen, JsonSerializer.Serialize(result.Report));
            Assert.Empty(LifecycleFixtures.Controls);
            harness.AssertNoPayload();
        }
        finally { release.TrySetResult(); }
    }

    [Fact]
    public async Task Actual_local_pipe_is_rejected_without_waiting_for_secret_bytes()
    {
        Assert.False(OperatingSystem.IsWindows(), "The full publication/pipe matrix requires a supported Unix platform.");
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var path = harness.File("secret-pipe", "");
        File.Delete(path);
        using var process = Process.Start(new ProcessStartInfo("mkfifo")
        { UseShellExecute = false, ArgumentList = { path } })!;
        try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)); }
        finally { if (!process.HasExited) { process.Kill(); } }
        Assert.Equal(0, process.ExitCode);
        using var anchor = File.OpenHandle(path, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite);
        await using var result = await ConfiguredFixtures.Registry().EvaluateConfigurationAsync(
            new(Document("file", path)), LifecycleFixtures.Versions, new(),
            new() { OperationTimeoutMilliseconds = 500 });
        Assert.Equal(HoardConfigurationOutcome.Failed, result.Outcome);
        Assert.Contains(result.Report.Diagnostics, d => d.Rule == HoardConfigurationRule.SecretUnavailable);
        Assert.Equal(0, result.Supervision.PendingCount);
        Assert.Empty(LifecycleFixtures.Controls);
    }

    [Fact]
    public async Task Environment_target_lookup_uses_platform_case_rules_without_an_alternate_lookup()
    {
        await using var result = await ConfiguredFixtures.Registry().EvaluateConfigurationAsync(
            new(Document(), environment: new Dictionary<string, string>(StringComparer.Ordinal)
            { [ConfigurationTestHarness.Locator.ToLowerInvariant()] = ConfigurationTestHarness.Credential }),
            LifecycleFixtures.Versions, new());
        Assert.Equal(OperatingSystem.IsWindows() ? HoardConfigurationOutcome.Validated : HoardConfigurationOutcome.Failed,
            result.Outcome);
    }

    [Fact]
    public async Task Shared_reference_resolves_each_owner_independently_without_cross_owner_options()
    {
        ConfiguredFixtures.Reset();
        var reads = 0;
        var builder = ConfiguredFixtures.Registry()
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol",
                Hoard.Abstractions.Modules.ModuleCategory.Protocol) with
            { Configuration = [new() { Key = "credential", Required = true, SecretReference = true, Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, ConfiguredFixtures.ConfiguredProtocolModule>()
            .AddModuleConfiguration<LifecycleFixtures.ProtocolProvider>(new(1, [new("credential", HoardOptionType.Secret, true)]));
        var root = JsonNode.Parse(Document())!;
        root["enabledmodules"]!.AsArray().Add("protocol");
        root["modules"]!["protocol"] = JsonNode.Parse(
            """{"optionsversion":1,"options":{"credential":{"kind":"env","target":"INVENTED_CONFIGURATION_SECRET"}}}""");
        await using var result = await builder.EvaluateConfigurationAsync(new(root.ToJsonString(), readEnvironment: (name, _) =>
        {
            Assert.Equal(ConfigurationTestHarness.Locator, name);
            return ValueTask.FromResult<string?>($"owner-{Interlocked.Increment(ref reads)}");
        }), LifecycleFixtures.Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, result.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(result.Configuration!);
        Assert.Equal(2, reads);
        Assert.Equal("owner-1", ConfiguredFixtures.Delivered!.GetSecret("credential").Reveal());
        Assert.Equal("owner-2", ConfiguredFixtures.ProtocolDelivered!.GetSecret("credential").Reveal());
        Assert.False(ConfiguredFixtures.ProtocolDelivered.Contains("label"));
        Assert.NotSame(ConfiguredFixtures.Delivered.GetSecret("credential"), ConfiguredFixtures.ProtocolDelivered.GetSecret("credential"));
    }

    [Fact]
    public async Task Concurrent_consume_dispose_mutation_and_legacy_attempts_have_one_secret_release_authority()
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var start = harness.Barrier();
        HoardSecretValue? secret = null;
        var builder = ConfiguredFixtures.Registry((context, _) =>
        {
            if (context.Phase == HoardOptionCheckPhase.Secrets) { secret = context.Options.GetSecret("credential"); }
            return ValueTask.FromResult(HoardOptionCheckResult.Accepted);
        });
        await using var evaluated = await builder.EvaluateConfigurationAsync(new(Document(), environment: harness.Environment),
            LifecycleFixtures.Versions, new());
        var legacy = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        var waiting = 0;
        async Task<HoardServiceComposition?> Consume(bool bare)
        {
            Interlocked.Increment(ref waiting);
            await start.Task;
            try
            {
                return bare ? await builder.ComposeHoardModulesAsync(legacy)
                    : await builder.ComposeHoardModulesAsync(evaluated.Configuration!);
            }
            catch (HoardLifecycleException failure)
            {
                Assert.All(failure.Diagnostics, d => Assert.Contains(d.RuleCode, new[] { "StaleConfiguration", "ConfigurationRequired" }));
                return null;
            }
        }
        var consumers = new[] { Task.Run(() => Consume(false)), Task.Run(() => Consume(false)), Task.Run(() => Consume(true)) };
        var dispose = Task.Run(async () =>
        { Interlocked.Increment(ref waiting); await start.Task; await evaluated.DisposeAsync(); });
        var mutate = Task.Run(async () =>
        { Interlocked.Increment(ref waiting); await start.Task; builder.AddModuleConfiguration<LifecycleFixtures.MetadataProvider>(ConfiguredFixtures.Contract); });
        foreach (var task in consumers) { harness.Observe(task); }
        harness.Observe(dispose);
        harness.Observe(mutate);
        await ConfigurationTestHarness.Until(() => Volatile.Read(ref waiting) == 5);
        start.TrySetResult();
        await Task.WhenAll(dispose, mutate).WaitAsync(TimeSpan.FromSeconds(5));
        var winners = (await Task.WhenAll(consumers).WaitAsync(TimeSpan.FromSeconds(5))).OfType<HoardServiceComposition>().ToArray();
        Assert.InRange(winners.Length, 0, 1);
        if (winners.Length == 1)
        {
            Assert.Equal(ConfigurationTestHarness.Credential, secret!.Reveal());
            Assert.Equal(1, LifecycleFixtures.For("metadata").Constructors);
            await winners[0].DisposeAsync();
        }
        else { Assert.Empty(LifecycleFixtures.Controls); }
        await ConfigurationTestHarness.Until(() => Released(secret!));
    }

    [Fact]
    public async Task Blocked_configured_delivery_keeps_transferred_secrets_and_prerequisites_without_late_services()
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        HoardSecretValue? secret = null;
        ConfiguredFixtures.OptionsHook = options =>
        {
            secret = options.GetSecret("credential");
            entered.TrySetResult();
            release.Task.GetAwaiter().GetResult();
            Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
        };
        var builder = ConfiguredFixtures.Registry(metadataDependsOnArtifact: true);
        await using var evaluation = await builder.EvaluateConfigurationAsync(new(Document(), environment: harness.Environment),
            LifecycleFixtures.Versions, new()
            {
                ActivationCallbackTimeout = TimeSpan.FromMilliseconds(50),
                ShutdownTimeout = TimeSpan.FromMilliseconds(100),
                DrainTimeout = TimeSpan.FromMilliseconds(10),
                ModuleCleanupTimeout = TimeSpan.FromMilliseconds(20)
            }, new() { TimeProvider = clock });
        var composing = builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        harness.Observe(composing);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await evaluation.DisposeAsync();
            await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(evaluation.Configuration!));
            Assert.Equal(ConfigurationTestHarness.Credential, secret!.Reveal());
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(50));
            clock.Advance(TimeSpan.FromMilliseconds(50));
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(10));
            clock.Advance(TimeSpan.FromMilliseconds(10));
            var failure = await Assert.ThrowsAsync<HoardLifecycleException>(() => composing.WaitAsync(TimeSpan.FromSeconds(5)));
            var frozen = JsonSerializer.Serialize(failure.Diagnostics);
            Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
            Assert.All(LifecycleFixtures.Controls.Values, c => Assert.DoesNotContain("stop", c.Calls));
            release.TrySetResult();
            await ConfigurationTestHarness.Until(() => Released(secret));
            Assert.DoesNotContain("services", LifecycleFixtures.For("metadata").Calls);
            Assert.All(LifecycleFixtures.Controls.Values, c => Assert.DoesNotContain("stop", c.Calls));
            Assert.Equal(frozen, JsonSerializer.Serialize(failure.Diagnostics));
        }
        finally { release.TrySetResult(); }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Pending_F02_notification_or_cancellation_retains_secrets_and_root_without_deferred_cleanup(bool cancellation)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var fail = harness.Barrier();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        var web = LifecycleFixtures.WebBuilder();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        web.Services.AddSingleton(_ => resource);
        HoardSecretValue? secret = null;
        void Hold()
        {
            Assert.Equal(ConfigurationTestHarness.Credential, secret!.Reveal());
            entered.TrySetResult();
            release.Task.GetAwaiter().GetResult();
            Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
            Assert.Equal(0, resource.Disposals);
        }
        CancellationTokenRegistration registration = default;
        LifecycleFixtures.For("artifact").Worker = async token =>
        {
            registration = token.Register(() => { if (cancellation) { Hold(); } });
            await fail.Task;
            throw new InvalidOperationException(ConfigurationTestHarness.Credential);
        };
        var builder = ConfiguredFixtures.Registry(services: web.Services, metadataDependsOnArtifact: true);
        await using var evaluation = await builder.EvaluateConfigurationAsync(new(Document(), environment: harness.Environment),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromMilliseconds(100), DrainTimeout = TimeSpan.FromMilliseconds(10) },
            new() { TimeProvider = clock });
        var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        secret = ConfiguredFixtures.Delivered!.GetSecret("credential");
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var notification = app.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopping.Register(
            () => { if (!cancellation) { Hold(); } });
        Task<HoardStopResult>? stopping = null;
        try
        {
            fail.TrySetResult();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            stopping = Task.Run(() => lease.Lifecycle.StopAsync());
            harness.Observe(stopping);
            await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(10));
            clock.Advance(TimeSpan.FromMilliseconds(10));
            var stopped = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, stopped.RootDisposal);
            await evaluation.DisposeAsync();
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            var frozen = JsonSerializer.Serialize(lease.StopResult);
            Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
            release.TrySetResult();
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            await ConfigurationTestHarness.Until(() => Released(secret));
            Assert.Equal(0, resource.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, c => Assert.DoesNotContain("stop", c.Calls));
            Assert.Equal(frozen, JsonSerializer.Serialize(lease.StopResult));
            Assert.DoesNotContain(ConfigurationTestHarness.Credential, frozen + string.Join("\n", LifecycleFixtures.LogCapture.Logs));
        }
        finally
        {
            fail.TrySetResult();
            release.TrySetResult();
            if (stopping is not null) { await stopping.WaitAsync(TimeSpan.FromSeconds(5)); }
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            registration.Dispose();
        }
    }

    private static bool Released(HoardSecretValue secret)
    {
        try { secret.Reveal(); return false; }
        catch (ObjectDisposedException) { return true; }
    }
}
