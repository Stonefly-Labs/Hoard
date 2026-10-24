using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Artifacts.ObjectSemantics;
using System.Diagnostics;
using System.Text.Json;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactAdmissionTests
{
    private static readonly ArtifactMaintenanceOptions Options = new();
    private static readonly ArtifactCleanupOptions Cleanup = new();

    [Fact]
    public async Task Concurrent_local_admission_keeps_native_volume_enumeration_safe()
    {
        await Task.WhenAll(Enumerable.Range(0, 16).Select(async _ =>
        {
            await using var driver = await ArtifactProviderDriver.CreateAsync("local");
            Assert.NotNull(driver.Identity);
        }));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Noncooperative_initialization_returns_with_owned_work_and_stop_does_not_release_it(string provider)
    {
        using var root = new ArtifactTestRoot();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        ValueTask Pause() { entered.TrySetResult(); return new(release.Task); }
        var local = new LocalFaultControls();
        var objects = new ObjectFaultControls();
        local.SetObserver("initialize.before-root", Pause);
        objects.SetObserver("object.initialize", Pause);
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        IArtifactStoreLifetime store = provider == "local" ? new LocalArtifactStore(root.Path, controls: local)
            : new ObjectArtifactStore(root.Path, controls: objects);
        var initialization = store.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity,
            new ArtifactCoordinationAuthority(identity)), new(TimeSpan.FromMilliseconds(100)), default).AsTask();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            var failure = Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(
                await initialization.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, failure.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failure.Cleanup);
            Assert.False(Directory.Exists(root.Path));
            var stop = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await store.StopAsync(new(TimeSpan.FromMilliseconds(20)), default).AsTask().WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stop.Code);
        }
        finally
        {
            release.TrySetResult();
            await initialization;
            var stopped = await store.StopAsync(new(), default);
            root.AllowCleanup = stopped is ArtifactResult<ArtifactShutdown>.Success;
            Assert.True(root.AllowCleanup);
        }
        Assert.False(Directory.Exists(root.Path));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Before_admission_and_with_mismatched_authority_no_source_or_directory_is_touched(string provider)
    {
        using var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var foreign = new ArtifactStoreIdentity(identity.ProviderModuleId, Guid.NewGuid(), Guid.NewGuid());
        var lifetime = Create(provider, root.Path);
        var store = Assert.IsAssignableFrom<IArtifactStore>(lifetime);
        Assert.Equal(ArtifactFailureCode.Disposed, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await lifetime.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, identity, new ArtifactCoordinationAuthority(foreign)), Options, default));
        Assert.False(Directory.Exists(root.Path));
        await lifetime.StopAsync(Cleanup, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Create_is_explicit_exclusive_and_disabled_construction_touches_no_directory(string provider)
    {
        using var root = new ArtifactTestRoot();
        var store = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(store);
        var first = Create(provider, root.Path);
        var second = Create(provider, root.Path);
        Assert.False(Directory.Exists(root.Path));
        var result = await first.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, store, authority), Options, default);
        var admitted = Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(result);
        Assert.True(admitted.Value.Capabilities.MeetsBaseline);
        Assert.True(Directory.Exists(root.Path));
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), Options, default));
        await second.StopAsync(Cleanup, default);
        await first.StopAsync(Cleanup, default);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), Options, default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Reopen_refuses_missing_foreign_incompatible_or_corrupt_roots_without_reset(string provider)
    {
        using var root = new ArtifactTestRoot();
        var store = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(store);
        var first = Create(provider, root.Path);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await first.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, store, authority), Options, default));
        Assert.False(Directory.Exists(root.Path));
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await first.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), Options, default));
        await first.StopAsync(Cleanup, default);
        var second = Create(provider, root.Path);
        var foreign = new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid());
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, foreign, new ArtifactCoordinationAuthority(foreign)), Options, default));
        await second.StopAsync(Cleanup, default);
        var manifest = Directory.GetFiles(root.Path, "*manifest*").Single();
        var original = File.ReadAllBytes(manifest);
        File.WriteAllBytes(manifest, [1, 2, 3]);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, store, authority), Options, default));
        Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(manifest));
        await second.StopAsync(Cleanup, default);
        File.WriteAllBytes(manifest, original);
    }

    [Fact]
    public async Task Local_reopen_preserves_identity_while_object_replacement_cannot_claim_durable_reopen()
    {
        foreach (var provider in new[] { "local", "object" })
        {
            using var root = new ArtifactTestRoot();
            var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
            var authority = new ArtifactCoordinationAuthority(identity);
            var first = Create(provider, root.Path);
            Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await first.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, authority), Options, default));
            await first.StopAsync(Cleanup, default);
            var second = Create(provider, root.Path);
            var result = await second.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, identity, authority), Options, default);
            if (provider == "local") { Assert.Equal(identity, Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(result).Value.Store); }
            else { Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(result); }
            await second.StopAsync(Cleanup, default);
        }
    }

    [Fact]
    public async Task Local_root_is_exclusively_owned_across_real_processes_not_a_lock_filename()
    {
        using var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
        var store = new LocalArtifactStore(root.Path);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await store.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, identity, new ArtifactCoordinationAuthority(identity)), Options, default));
        Assert.False(await ChildAdmission(root, identity));
        await store.StopAsync(Cleanup, default);
        Assert.True(await ChildAdmission(root, identity));
    }

    private static async Task<bool> ChildAdmission(ArtifactTestRoot root, ArtifactStoreIdentity identity)
    {
        var binary = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_CRASH_RUNNER")
            ?? throw new InvalidOperationException("Artifact child proof requires its prepared package-only runner.");
        var start = new ProcessStartInfo("dotnet") { RedirectStandardOutput = true, RedirectStandardError = true };
        foreach (var argument in new[] { binary, "admission", root.Path, identity.ProviderModuleId,
            identity.InstanceId.ToString(), identity.Epoch.ToString() }) { start.ArgumentList.Add(argument); }
        root.AllowCleanup = false;
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Artifact owned child did not start.");
        var output = ArtifactChildOutput.ReadToEndAsync(process.StandardOutput);
        var errors = ArtifactChildOutput.ReadToEndAsync(process.StandardError);
        try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(15)); }
        finally
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
                await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));
            }
            root.AllowCleanup = process.HasExited;
        }
        Assert.Equal(0, process.ExitCode);
        Assert.Empty(await errors);
        using var document = JsonDocument.Parse(await output);
        Assert.Equal(process.Id, document.RootElement.GetProperty("pid").GetInt32());
        return document.RootElement.GetProperty("admitted").GetBoolean();
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Symlinked_root_or_ancestor_is_rejected_without_touching_outside_sentinel(string provider)
    {
        if (OperatingSystem.IsWindows()) { throw new InvalidOperationException("This qualification requires a Unix host."); }
        using var root = new ArtifactTestRoot();
        Directory.CreateDirectory(root.Path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        var sentinel = System.IO.Path.Combine(root.Path, "sentinel");
        File.WriteAllText(sentinel, ArtifactTestData.Canary);
        var link = root.Path + "-link";
        Directory.CreateSymbolicLink(link, root.Path);
        try
        {
            var identity = new ArtifactStoreIdentity($"fixture.artifact.{provider}", Guid.NewGuid(), Guid.NewGuid());
            var authority = new ArtifactCoordinationAuthority(identity);
            var first = Create(provider, System.IO.Path.Combine(link, "child"));
            Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await first.InitializeAsync(
                new(ArtifactInitializationMode.CreateEmpty, identity, authority), Options, default));
            Assert.Equal(ArtifactTestData.Canary, File.ReadAllText(sentinel));
            Assert.False(Directory.Exists(System.IO.Path.Combine(root.Path, "child")));
            await first.StopAsync(Cleanup, default);
        }
        finally { Directory.Delete(link); }
    }

    private static IArtifactStoreLifetime Create(string provider, string root)
        => provider == "local" ? new LocalArtifactStore(root) : new ObjectArtifactStore(root);
}

internal sealed class ArtifactTestRoot : IDisposable
{
    private readonly string parent;
    public ArtifactTestRoot()
    {
        parent = System.IO.Path.GetFullPath(Environment.GetEnvironmentVariable("HOARD_ARTIFACT_TEST_ROOT")
            ?? ".foundation/artifact-contract-tests");
        Directory.CreateDirectory(parent);
        Path = System.IO.Path.Combine(parent, Guid.NewGuid().ToString("N"));
    }
    public string Path { get; }
    public bool AllowCleanup { get; set; } = true;
    public void Dispose()
    {
        if (System.IO.Path.GetDirectoryName(Path) != parent) { throw new InvalidOperationException("Unowned test root."); }
        if (!AllowCleanup) { return; }
        if (Directory.Exists(Path)) { Directory.Delete(Path, recursive: true); }
    }
}
