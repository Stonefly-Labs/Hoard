using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;

namespace Hoard.Conformance.Tests;

public sealed class OwnedResourceTests
{
    [Fact]
    public async Task Original_controller_descriptor_supplies_one_exact_resource_without_releasing_its_pin()
    {
        using var fixture = new Fixture();
        using var controller = OwnedDirectoryHandle.OpenPrivateParent(fixture.Root);
        controller.Lock();
        var descriptor = controller.DangerousGetHandle().ToInt32();
        var resource = new ConformanceOwnedDirectory("controller-resource", fixture.Root);
        using (var source = ConformanceResourceAllocator.OpenControllerLease(
            resource, descriptor, fixture.Repository, recovery: false))
        {
            Assert.Same(resource, await source.AllocateDirectoryAsync(default));
            await Assert.ThrowsAsync<InvalidOperationException>(() => source.AllocateDirectoryAsync(default).AsTask());
            File.WriteAllText(Path.Combine(resource.DirectoryPath, "state"), "owned");
            await source.ReleaseAsync(resource, Task.CompletedTask, default);
        }
        controller.VerifyPath(fixture.Root);
        Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.OpenControllerLease(
            resource, descriptor, fixture.Repository, recovery: false));
        using (var recovery = ConformanceResourceAllocator.OpenControllerLease(
            resource, descriptor, fixture.Repository, recovery: true))
        {
            Assert.Same(resource, await recovery.AllocateDirectoryAsync(default));
            var actual = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            Assert.Equal(ConformanceOwnershipState.Retained,
                (await recovery.ReleaseAsync(resource, actual.Task, new CancellationToken(true))).State);
            Assert.Throws<InvalidOperationException>(() => recovery.Dispose());
            actual.SetResult();
            await recovery.ReleaseAsync(resource, actual.Task, default);
            Assert.DoesNotContain(recovery.ObserveLedger(), row => row.Observation.State == ConformanceOwnershipState.Released);
        }
        controller.VerifyPath(fixture.Root);
        Assert.Equal("owned", File.ReadAllText(Path.Combine(resource.DirectoryPath, "state")));
        File.Delete(Path.Combine(resource.DirectoryPath, "state"));
    }

    [Fact]
    public void Controller_descriptor_cannot_admit_a_foreign_path_replaced_inode_or_standard_stream()
    {
        using var fixture = new Fixture();
        using var foreign = new Fixture();
        using var controller = OwnedDirectoryHandle.OpenPrivateParent(fixture.Root);
        var descriptor = controller.DangerousGetHandle().ToInt32();
        Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.OpenControllerLease(
            new("foreign-resource", foreign.Root), descriptor, fixture.Repository, recovery: true));
        Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.OpenControllerLease(
            new("controller-resource", fixture.Root), 0, fixture.Repository, recovery: true));
        var parked = fixture.Root + "-parked";
        Directory.Move(fixture.Root, parked);
        Directory.CreateDirectory(fixture.Root);
        if (!OperatingSystem.IsWindows()) { File.SetUnixFileMode(fixture.Root, Fixture.PrivateMode); }
        try
        {
            Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.OpenControllerLease(
                new("controller-resource", fixture.Root), descriptor, fixture.Repository, recovery: true));
        }
        finally
        {
            Directory.Delete(fixture.Root);
            Directory.Move(parked, fixture.Root);
        }
        controller.VerifyPath(fixture.Root);
    }

    [Fact]
    public async Task Fresh_private_leases_reject_forged_foreign_and_second_writer_authority()
    {
        using var fixture = new Fixture();
        using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository);
        using var foreignFixture = new Fixture();
        using var foreign = ConformanceResourceAllocator.Open(foreignFixture.Root, foreignFixture.Repository);
        Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository));
        var first = await allocator.AllocateDirectoryAsync(default);
        var second = await allocator.AllocateDirectoryAsync(default);
        Assert.NotEqual(first.ResourceId, second.ResourceId);
        Assert.Empty(Directory.EnumerateFileSystemEntries(first.DirectoryPath));
        if (!OperatingSystem.IsWindows())
        {
            Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute,
                File.GetUnixFileMode(first.DirectoryPath));
        }
        var forged = new ConformanceOwnedDirectory(first.ResourceId, first.DirectoryPath);
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await allocator.ReleaseAsync(forged, default));
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await foreign.ReleaseAsync(first, default));
        Assert.True(Directory.Exists(first.DirectoryPath));
        await allocator.ReleaseAsync(first, Task.CompletedTask, default);
        await allocator.ReleaseAsync(second, Task.CompletedTask, default);
        using var recovery = allocator.OpenRecovery(first);
        Assert.Same(first, await recovery.AllocateDirectoryAsync(default));
        var recovering = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Assert.Equal(ConformanceOwnershipState.Retained,
            (await recovery.ReleaseAsync(first, recovering.Task, new CancellationToken(true))).State);
        Assert.Equal("CleanupIncomplete", Assert.Throws<InvalidOperationException>(() => recovery.Dispose()).Message);
        Assert.Equal("CleanupIncomplete", Assert.Throws<InvalidOperationException>(() => allocator.Dispose()).Message);
        Assert.True(Directory.Exists(first.DirectoryPath));
        recovering.SetResult();
        await recovery.ReleaseAsync(first, recovering.Task, default);
        recovery.Dispose();
        allocator.Dispose();
        Directory.Delete(first.DirectoryPath);
        Directory.Delete(second.DirectoryPath);
    }

    [Fact]
    public async Task Same_path_and_copied_marker_do_not_replace_native_directory_identity()
    {
        using var fixture = new Fixture();
        using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository);
        var resource = await allocator.AllocateDirectoryAsync(default);
        await allocator.ReleaseAsync(resource, Task.CompletedTask, default);
        File.WriteAllText(Path.Combine(resource.DirectoryPath, "marker"), resource.ResourceId);
        var original = resource.DirectoryPath + "-original";
        Directory.Move(resource.DirectoryPath, original);
        Directory.CreateDirectory(resource.DirectoryPath);
        if (!OperatingSystem.IsWindows()) { File.SetUnixFileMode(resource.DirectoryPath, Fixture.PrivateMode); }
        File.Copy(Path.Combine(original, "marker"), Path.Combine(resource.DirectoryPath, "marker"));
        Assert.Equal("OwnershipInvalid", Assert.Throws<InvalidOperationException>(
            () => allocator.OpenRecovery(resource)).Message);
        var failure = await Assert.ThrowsAsync<InvalidOperationException>(
            async () => await allocator.ReleaseAsync(resource, default));
        Assert.Equal("OwnershipInvalid", failure.Message);
        Assert.Equal(ConformanceDiagnosticCode.OwnershipInvalid,
            allocator.ObserveLedger()[^1].Observation.Reason);
        Assert.True(File.Exists(Path.Combine(original, "marker")));
        Assert.True(File.Exists(Path.Combine(resource.DirectoryPath, "marker")));
        allocator.Dispose();
        File.Delete(Path.Combine(original, "marker"));
        File.Delete(Path.Combine(resource.DirectoryPath, "marker"));
        Directory.Delete(original);
        Directory.Delete(resource.DirectoryPath);
    }

    [Fact]
    public async Task Symlink_ancestors_parent_swaps_and_permissions_cannot_redirect_ownership()
    {
        using var fixture = new Fixture();
        var link = fixture.Root + "-link";
        Directory.CreateSymbolicLink(link, fixture.Root);
        try
        {
            Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.Open(link, fixture.Repository));
        }
        finally { Directory.Delete(link); }
        using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository);
        var resource = await allocator.AllocateDirectoryAsync(default);
        await allocator.ReleaseAsync(resource, Task.CompletedTask, default);
        using var foreign = new Fixture();
        var sentinel = Path.Combine(foreign.Root, "outside-sentinel");
        File.WriteAllText(sentinel, "untouched");
        var parked = resource.DirectoryPath + "-parked";
        Directory.Move(resource.DirectoryPath, parked);
        Directory.CreateSymbolicLink(resource.DirectoryPath, foreign.Root);
        try
        {
            Assert.Equal("OwnershipInvalid", Assert.Throws<InvalidOperationException>(
                () => allocator.OpenRecovery(resource)).Message);
            await Assert.ThrowsAsync<InvalidOperationException>(
                async () => await allocator.ReleaseAsync(resource, default));
            Assert.Equal("untouched", File.ReadAllText(sentinel));
        }
        finally
        {
            Directory.Delete(resource.DirectoryPath);
            Directory.Move(parked, resource.DirectoryPath);
            File.Delete(sentinel);
        }
        var moved = fixture.Root + "-moved";
        Directory.Move(fixture.Root, moved);
        Directory.CreateSymbolicLink(fixture.Root, moved);
        try
        {
            await Assert.ThrowsAsync<InvalidOperationException>(
                async () => await allocator.AllocateDirectoryAsync(default));
            await Assert.ThrowsAsync<InvalidOperationException>(
                async () => await allocator.ReleaseAsync(resource, default));
            Assert.Empty(Directory.GetFiles(moved));
        }
        finally
        {
            Directory.Delete(fixture.Root);
            Directory.Move(moved, fixture.Root);
        }
        if (!OperatingSystem.IsWindows())
        {
            File.SetUnixFileMode(fixture.Root, Fixture.PrivateMode | UnixFileMode.GroupRead);
            Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository));
            File.SetUnixFileMode(fixture.Root, Fixture.PrivateMode);
        }
        Assert.Throws<InvalidOperationException>(() => ConformanceResourceAllocator.Open(fixture.Repository, fixture.Repository));
        allocator.Dispose();
        Directory.Delete(resource.DirectoryPath);
    }

    [Fact]
    public async Task Caller_timeout_and_cancellation_retain_live_work_and_retry_preserves_failure()
    {
        using var fixture = new Fixture();
        using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository, TimeSpan.FromMilliseconds(20));
        IConformanceResourceAllocator typedAllocator = allocator;
        var resource = await allocator.AllocateDirectoryAsync(default);
        var work = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var deferred = await allocator.ReleaseAsync(resource, default);
        Assert.Equal(ConformanceOwnershipState.Settling, deferred.State);
        var timeout = await typedAllocator.ReleaseAsync(resource, work.Task, default);
        Assert.Equal(ConformanceOwnershipState.Retained, timeout.State);
        Assert.Equal(ConformanceDiagnosticCode.CleanupIncomplete, timeout.Reason);
        Assert.False(work.Task.IsCompleted);
        Assert.Equal("CleanupIncomplete", Assert.Throws<InvalidOperationException>(
            () => allocator.OpenRecovery(resource)).Message);
        Assert.Throws<InvalidOperationException>(() => allocator.Dispose());
        Assert.Equal(ConformanceOwnershipState.Retained, (await allocator.ReleaseAsync(resource, default)).State);
        var frozen = allocator.ObserveLedger();
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var cancelled = await allocator.ReleaseAsync(resource, work.Task, cancellation.Token);
        Assert.Equal(ConformanceOwnershipState.Retained, cancelled.State);
        Assert.False(work.Task.IsCompleted);
        work.SetResult();
        var settled = await allocator.ReleaseAsync(resource, work.Task, default);
        Assert.Equal(ConformanceOwnershipState.Settling, settled.State);
        Assert.Equal<string>([resource.ResourceId], settled.ResourceIds);
        Assert.True(Directory.Exists(resource.DirectoryPath));
        var history = allocator.ObserveLedger();
        Assert.Contains(history, item => item.Observation.State == ConformanceOwnershipState.Retained);
        Assert.True(history.Length > frozen.Length);
        Assert.Equal(ConformanceOwnershipState.Retained, frozen[^1].Observation.State);
        Assert.DoesNotContain(history, item => item.Observation.State == ConformanceOwnershipState.Released);
        allocator.Dispose();
        Directory.Delete(resource.DirectoryPath);
    }

    [Fact]
    public async Task Provider_task_failure_is_sanitized_and_cannot_be_replaced_by_a_success_task()
    {
        using var fixture = new Fixture();
        using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository);
        var resource = await allocator.AllocateDirectoryAsync(default);
        var failedTask = Task.FromException(new IOException("private-canary"));
        var retained = await allocator.ReleaseAsync(resource, failedTask, default);
        Assert.Equal(ConformanceOwnershipState.Retained, retained.State);
        Assert.Equal(ConformanceDiagnosticCode.CleanupIncomplete, retained.Reason);
        await Assert.ThrowsAsync<InvalidOperationException>(
            async () => await allocator.ReleaseAsync(resource, Task.CompletedTask, default));
        Assert.True(Directory.Exists(resource.DirectoryPath));
        allocator.Dispose();
        Directory.Delete(resource.DirectoryPath);
    }

    [Fact]
    public void Preexisting_store_is_not_adopted_even_when_parent_permissions_are_private()
    {
        using var fixture = new Fixture();
        var sentinel = Path.Combine(fixture.Root, "existing-user-store");
        File.WriteAllText(sentinel, "untouched");
        try
        {
            Assert.Throws<InvalidOperationException>(() =>
            {
                using var allocator = ConformanceResourceAllocator.Open(fixture.Root, fixture.Repository);
            });
            Assert.Equal("untouched", File.ReadAllText(sentinel));
        }
        finally { File.Delete(sentinel); }
    }

    private sealed class Fixture : IDisposable
    {
        internal const UnixFileMode PrivateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute;
        internal Fixture()
        {
            Repository = FindRepository();
            var parent = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Hoard", "conformance-owned-tests");
            Directory.CreateDirectory(parent);
            Root = Path.Combine(parent, "owned-" + Guid.NewGuid().ToString("N"));
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
            Directory.CreateDirectory(Root, PrivateMode);
        }
        internal string Root { get; }
        internal string Repository { get; }
        public void Dispose()
        {
            // Test-only fixture teardown: all test tasks have ended; production allocator never deletes.
            Directory.Delete(Root);
        }
        private static string FindRepository()
        {
            for (var current = new DirectoryInfo(AppContext.BaseDirectory); current is not null; current = current.Parent)
            {
                if (File.Exists(Path.Combine(current.FullName, "Hoard.slnx"))) { return current.FullName; }
            }
            throw new InvalidOperationException("PrerequisiteMissing");
        }
    }
}
