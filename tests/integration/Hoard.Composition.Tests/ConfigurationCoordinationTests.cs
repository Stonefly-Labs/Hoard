using System.Text.Json;
using Hoard.Hosting.Configuration;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationCoordinationTests
{
    [Theory]
    [InlineData("credential", "env", false)]
    [InlineData("alternate", "env", false)]
    [InlineData("credential", "file", false)]
    [InlineData("alternate", "file", false)]
    [InlineData("credential", "env", true)]
    [InlineData("alternate", "env", true)]
    [InlineData("credential", "file", true)]
    [InlineData("alternate", "file", true)]
    public async Task Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault(
        string field, string kind, bool cancelled)
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        using var caller = new CancellationTokenSource();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var notified = harness.Barrier();
        var notificationRelease = harness.Barrier();
        var workRelease = harness.Barrier();
        async ValueTask<string> Read(CancellationToken token)
        {
            using var registration = token.Register(() =>
            {
                notified.TrySetResult();
                notificationRelease.Task.GetAwaiter().GetResult();
                throw new InvalidOperationException(ConfigurationTestHarness.Credential);
            });
            entered.TrySetResult();
            await workRelease.Task;
            throw new IOException(ConfigurationTestHarness.Credential);
        }
        var work = ConfigurationSecretTests.TwoSecretRegistry().EvaluateConfigurationAsync(new(ConfiguredFixtures.Defaults,
            arguments: ConfigurationSecretTests.SecretArguments(field, kind),
            readEnvironment: async (_, token) => await Read(token),
            readFile: (_, token) => Read(token)), LifecycleFixtures.Versions, new(),
            new() { TimeProvider = clock, OperationTimeoutMilliseconds = 50 }, caller.Token);
        harness.Observe(work);
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (cancelled) { caller.Cancel(); }
            else
            {
                await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(50));
                clock.Advance(TimeSpan.FromMilliseconds(50));
            }
            await notified.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await using var result = await work.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(cancelled ? HoardConfigurationOutcome.Cancelled : HoardConfigurationOutcome.TimedOut, result.Outcome);
            Assert.Null(result.Configuration);
            var frozen = JsonSerializer.Serialize(result.Report);
            var failure = Assert.Single(result.Report.Diagnostics);
            Assert.Equal(cancelled ? HoardConfigurationRule.Cancelled : HoardConfigurationRule.Timeout, failure.Rule);
            AssertOrigin(failure);
            await result.DisposeAsync();
            Assert.True(result.Supervision.PendingCount >= 2);
            notificationRelease.TrySetResult();
            await ConfigurationTestHarness.Until(() => result.Supervision.Diagnostics.Any(
                d => d.Rule == HoardConfigurationRule.CancellationFailure));
            workRelease.TrySetResult();
            await ConfigurationTestHarness.Until(() => result.Supervision.PendingCount == 0);
            AssertOrigin(Assert.Single(result.Supervision.Diagnostics.Where(d => d.Rule == HoardConfigurationRule.CancellationFailure)));
            AssertOrigin(Assert.Single(result.Supervision.Diagnostics.Where(d => d.Rule == HoardConfigurationRule.LateCheckFailure)));
            Assert.Equal(frozen, JsonSerializer.Serialize(result.Report));
            Assert.Empty(LifecycleFixtures.Controls);
            var output = JsonSerializer.Serialize(result);
            Assert.DoesNotContain(ConfigurationTestHarness.Credential, output);
            Assert.DoesNotContain(ConfigurationTestHarness.Locator, output);
            Assert.DoesNotContain("/invented/configuration-secret", output);
            harness.AssertNoPayload("/invented/configuration-secret");
        }
        finally { notificationRelease.TrySetResult(); workRelease.TrySetResult(); }

        void AssertOrigin(HoardConfigurationDiagnostic diagnostic)
        {
            Assert.Equal("protocol", diagnostic.Owner);
            Assert.Equal($"modules:protocol:options:{field}", diagnostic.Setting);
            Assert.Equal(HoardConfigurationSource.CommandLine, diagnostic.Source);
            Assert.Equal(HoardConfigurationPhase.Secrets, diagnostic.Phase);
        }
    }

    [Fact]
    public async Task Entire_synchronous_callback_is_supervised_and_late_fault_is_observed()
    {
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var entered = harness.Barrier();
        var release = harness.Barrier();
        var evaluationTask = LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, explicitFile: "/invented",
                readFile: (_, _) =>
                {
                    entered.TrySetResult();
                    release.Task.GetAwaiter().GetResult();
                    throw new InvalidOperationException(ConfigurationTestHarness.Credential);
                }),
            LifecycleFixtures.Versions, new(),
            new() { TimeProvider = clock, OperationTimeoutMilliseconds = 50, EvaluationTimeoutMilliseconds = 100 });
        harness.Observe(evaluationTask);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        await ConfigurationTestHarness.Until(() => clock.PendingTimers > 0);
        clock.Advance(TimeSpan.FromMilliseconds(49));
        Assert.False(evaluationTask.IsCompleted);
        clock.Advance(TimeSpan.FromMilliseconds(1));
        await using var evaluation = await evaluationTask.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.Equal(HoardConfigurationOutcome.TimedOut, evaluation.Outcome);
        Assert.True(evaluation.Supervision.PendingCount > 0);
        await evaluation.DisposeAsync();
        Assert.True(evaluation.Supervision.PendingCount > 0);
        release.TrySetResult();
        await ConfigurationTestHarness.Until(() => evaluation.Supervision.PendingCount == 0);
        Assert.Equal(HoardConfigurationOutcome.TimedOut, evaluation.Outcome);
        Assert.Contains(evaluation.Supervision.Diagnostics, item => item.Rule == HoardConfigurationRule.LateCheckFailure);
        harness.AssertNoPayload();
    }

    [Fact]
    public async Task Caller_cancellation_does_not_run_collaborator_notification_inline()
    {
        await using var harness = new ConfigurationTestHarness();
        using var caller = new CancellationTokenSource();
        var entered = harness.Barrier();
        var notified = harness.Barrier();
        var release = harness.Barrier();
        var workRelease = harness.Barrier();
        var evaluationTask = LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, explicitFile: "/invented",
                readFile: async (_, token) =>
                {
                    using var registration = token.Register(() =>
                    {
                        notified.TrySetResult();
                        release.Task.GetAwaiter().GetResult();
                        throw new InvalidOperationException(ConfigurationTestHarness.Credential);
                    });
                    entered.TrySetResult();
                    await workRelease.Task;
                    return ConfigurationFixtures.Defaults;
                }), LifecycleFixtures.Versions, new(), cancellationToken: caller.Token);
        harness.Observe(evaluationTask);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        caller.Cancel();
        await notified.Task.WaitAsync(TimeSpan.FromSeconds(5));
        await using var evaluation = await evaluationTask.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.Equal(HoardConfigurationOutcome.Cancelled, evaluation.Outcome);
        Assert.True(evaluation.Supervision.PendingCount >= 2);
        await evaluation.DisposeAsync();
        release.TrySetResult();
        workRelease.TrySetResult();
        await ConfigurationTestHarness.Until(() => evaluation.Supervision.PendingCount == 0);
        Assert.Contains(evaluation.Supervision.Diagnostics, item => item.Rule == HoardConfigurationRule.CancellationFailure);
    }

    [Fact]
    public async Task Already_cancelled_input_dispatches_nothing()
    {
        using var caller = new CancellationTokenSource();
        caller.Cancel();
        var reads = 0;
        await using var result = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, explicitFile: "/invented",
                readFile: (_, _) => { reads++; return ValueTask.FromResult(ConfigurationFixtures.Defaults); }),
            LifecycleFixtures.Versions, new(), cancellationToken: caller.Token);
        Assert.Equal(HoardConfigurationOutcome.Cancelled, result.Outcome);
        Assert.Equal(0, reads);
    }

    [Fact]
    public async Task Absolute_deadline_caps_the_next_dispatch_and_prevents_later_work()
    {
        await using var harness = new ConfigurationTestHarness();
        var clock = new LifecycleTestTimeProvider();
        var supervisor = new ConfigurationSupervisor(new()
        {
            TimeProvider = clock,
            EvaluationTimeoutMilliseconds = 100,
            OperationTimeoutMilliseconds = 80
        }, CancellationToken.None);
        var release = harness.Barrier();
        var entered = harness.Barrier();
        var first = supervisor.RunAsync(HoardConfigurationPhase.PublicOptions, HoardConfigurationSource.Defaults,
            "configuration", async _ => { entered.TrySetResult(); await release.Task; return true; });
        harness.Observe(first);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        await ConfigurationTestHarness.Until(() => clock.PendingTimers > 0);
        clock.Advance(TimeSpan.FromMilliseconds(70));
        release.TrySetResult();
        await first.WaitAsync(TimeSpan.FromSeconds(5));
        var secondRelease = harness.Barrier();
        var second = supervisor.RunAsync(HoardConfigurationPhase.Secrets, HoardConfigurationSource.File,
            "configuration", async _ => { await secondRelease.Task; return true; });
        harness.Observe(second);
        await ConfigurationTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(30));
        clock.Advance(TimeSpan.FromMilliseconds(30));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => second);
        var calls = 0;
        await Assert.ThrowsAsync<ConfigurationFailure>(() => supervisor.RunAsync(
            HoardConfigurationPhase.SecretOptions, HoardConfigurationSource.Defaults, "configuration",
            _ => { calls++; return ValueTask.FromResult(true); }));
        Assert.Equal(0, calls);
        supervisor.Complete(false);
        supervisor.Dispose();
        secondRelease.TrySetResult();
        await ConfigurationTestHarness.Until(() => supervisor.Snapshot.PendingCount == 0);
    }

    [Fact]
    public async Task Pending_work_keeps_sensitive_inputs_alive_after_bounded_disposal()
    {
        await using var harness = new ConfigurationTestHarness();
        using var caller = new CancellationTokenSource();
        var supervisor = new ConfigurationSupervisor(new(), caller.Token);
        var secret = new HoardSecretValue(ConfigurationTestHarness.Credential);
        supervisor.Hold(new OwnerOptionsLease(new(new Dictionary<string, object> { ["credential"] = secret })));
        var entered = harness.Barrier();
        var release = harness.Barrier();
        var work = supervisor.RunAsync(HoardConfigurationPhase.SecretOptions, HoardConfigurationSource.Environment,
            "configuration", async _ =>
            {
                entered.TrySetResult();
                await release.Task;
                Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
                return true;
            });
        harness.Observe(work);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        caller.Cancel();
        await Assert.ThrowsAsync<ConfigurationFailure>(() => work);
        supervisor.Complete(false);
        supervisor.Dispose();
        Assert.Equal(ConfigurationTestHarness.Credential, secret.Reveal());
        release.TrySetResult();
        await ConfigurationTestHarness.Until(() => supervisor.Snapshot.PendingCount == 0);
        Assert.Throws<ObjectDisposedException>(() => secret.Reveal());
    }

    [Fact]
    public async Task Elapsed_dispatch_cap_wins_even_when_timeout_notification_is_delayed()
    {
        var clock = new LaggedTimerClock();
        await using var result = await LifecycleFixtures.Registry().EvaluateConfigurationAsync(
            new(ConfigurationFixtures.Defaults, explicitFile: "/invented",
                readFile: (_, _) =>
                {
                    clock.Elapsed += TimeSpan.FromMilliseconds(6);
                    return ValueTask.FromResult(ConfigurationFixtures.Defaults);
                }), LifecycleFixtures.Versions, new(),
            new() { TimeProvider = clock, OperationTimeoutMilliseconds = 5, EvaluationTimeoutMilliseconds = 100 });
        Assert.Equal(HoardConfigurationOutcome.TimedOut, result.Outcome);
        Assert.Contains(result.Report.Diagnostics, item => item.Rule == HoardConfigurationRule.Timeout);
    }

    [Fact]
    public async Task Cancellation_at_success_boundary_prevents_completion_and_notification_retains_inputs()
    {
        await using var harness = new ConfigurationTestHarness();
        using var caller = new CancellationTokenSource();
        var supervisor = new ConfigurationSupervisor(new(), caller.Token);
        var probe = new DisposalProbe();
        var entered = harness.Barrier();
        var notified = harness.Barrier();
        var release = harness.Barrier();
        var callbackRelease = harness.Barrier();
        supervisor.Hold(probe);
        var work = supervisor.RunAsync(HoardConfigurationPhase.Sources, HoardConfigurationSource.File,
            "configuration", async token =>
            {
                using var registration = token.Register(() =>
                {
                    notified.TrySetResult();
                    release.Task.GetAwaiter().GetResult();
                    Assert.False(probe.Released);
                });
                entered.TrySetResult();
                await callbackRelease.Task;
                return true;
            });
        harness.Observe(work);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        caller.Cancel();
        await notified.Task.WaitAsync(TimeSpan.FromSeconds(5));
        await Assert.ThrowsAsync<ConfigurationFailure>(() => work);
        Assert.Throws<ConfigurationFailure>(() => supervisor.Complete(true));
        supervisor.Complete(false);
        supervisor.Dispose();
        Assert.False(probe.Released);
        callbackRelease.TrySetResult();
        release.TrySetResult();
        await ConfigurationTestHarness.Until(() => supervisor.Snapshot.PendingCount == 0);
        Assert.True(probe.Released);
    }

    private sealed class DisposalProbe : IDisposable
    {
        internal bool Released { get; private set; }
        public void Dispose() => Released = true;
    }

    private sealed class LaggedTimerClock : TimeProvider
    {
        private readonly LifecycleTestTimeProvider timers = new();
        internal TimeSpan Elapsed { get; set; }
        public override long TimestampFrequency => TimeSpan.TicksPerSecond;
        public override long GetTimestamp() => Elapsed.Ticks;
        public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period) =>
            timers.CreateTimer(callback, state, dueTime, period);
    }
}
