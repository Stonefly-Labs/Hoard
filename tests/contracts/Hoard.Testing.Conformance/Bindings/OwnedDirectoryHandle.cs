using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace Hoard.Testing.Conformance.Bindings;

// All native directory identity and creation operations are centralized here.
internal sealed class OwnedDirectoryHandle : SafeHandleZeroOrMinusOneIsInvalid
{
    private const int DirectoryType = 0x4000;
    private static bool Mac => OperatingSystem.IsMacOS();
    // Linux arm64 overrides the generic UAPI O_DIRECTORY/O_NOFOLLOW values.
    private static int OpenFlags => Mac ? 0x100000 | 0x100 | 0x1000000
        : RuntimeInformation.ProcessArchitecture == Architecture.Arm64
            ? 0x4000 | 0x8000 | 0x80000 : 0x10000 | 0x20000 | 0x80000;
    private readonly Identity identity;

    private OwnedDirectoryHandle(int descriptor) : base(true)
    {
        SetHandle(descriptor);
        try { identity = ReadIdentity(descriptor); }
        catch { Dispose(); throw; }
    }

    internal static string Normalize(string path)
    {
        if (string.IsNullOrEmpty(path) || !Path.IsPathFullyQualified(path)
            || path.Split(Path.DirectorySeparatorChar).Any(part => part is "." or ".."))
        { throw new InvalidOperationException("OwnershipInvalid"); }
        return Path.TrimEndingDirectorySeparator(Path.GetFullPath(path));
    }

    internal static OwnedDirectoryHandle OpenPrivateParent(string path)
    {
        RequirePlatform();
        var result = OpenChain(path);
        try
        {
            result.CheckPrivate();
            return result;
        }
        catch { result.Dispose(); throw; }
    }

    private static void RequirePlatform()
    {
        if (!Mac && !OperatingSystem.IsLinux()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
        if (RuntimeInformation.ProcessArchitecture is not (Architecture.X64 or Architecture.Arm64))
        { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
    }

    private static OwnedDirectoryHandle OpenChain(string path)
    {
        var descriptor = Open("/", OpenFlags);
        if (descriptor < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
        var current = new OwnedDirectoryHandle(descriptor);
        try
        {
            var prefix = "/";
            foreach (var part in path.Split('/', StringSplitOptions.RemoveEmptyEntries))
            {
                prefix = Path.Combine(prefix, part);
                if (File.Exists(Path.Combine(prefix, ".git")) || Directory.Exists(Path.Combine(prefix, ".git")))
                { throw new InvalidOperationException("OwnershipInvalid"); }
                var next = OpenAt(current.Descriptor, part, OpenFlags);
                if (next < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
                var opened = new OwnedDirectoryHandle(next);
                current.Dispose();
                current = opened;
            }
            return current;
        }
        catch { current.Dispose(); throw; }
    }

    internal void Lock()
    {
        if (Flock(Descriptor, 2 | 4) != 0) { throw new InvalidOperationException("OwnershipInvalid"); }
    }

    internal static OwnedDirectoryHandle Duplicate(int descriptor)
    {
        RequirePlatform();
        if (descriptor < 3) { throw new InvalidOperationException("OwnershipInvalid"); }
        var copy = Dup(descriptor);
        if (copy < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
        var result = new OwnedDirectoryHandle(copy);
        try
        {
            // FIOCLEX needs no variadic argument, including on Darwin arm64.
            if (Ioctl(copy, Mac ? 0x20006601u : 0x5451u) != 0)
            { throw new InvalidOperationException("OwnershipInvalid"); }
            result.CheckPrivate();
            return result;
        }
        catch { result.Dispose(); throw; }
    }

    internal OwnedDirectoryHandle CreateChild(string name)
    {
        if (MkdirAt(Descriptor, name, 0x1c0) != 0) { throw new InvalidOperationException("OwnershipInvalid"); }
        var descriptor = OpenAt(Descriptor, name, OpenFlags);
        if (descriptor < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
        var result = new OwnedDirectoryHandle(descriptor);
        return result;
    }

    internal OwnedDirectoryHandle OpenRelativeDirectory(string relative)
    {
        var current = Duplicate(Descriptor);
        try
        {
            foreach (var part in relative.Split('/', StringSplitOptions.RemoveEmptyEntries))
            {
                var descriptor = OpenAt(current.Descriptor, part, OpenFlags);
                if (descriptor < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
                var next = new OwnedDirectoryHandle(descriptor);
                current.Dispose();
                current = next;
                current.CheckPrivate();
            }
            return current;
        }
        catch { current.Dispose(); throw; }
    }

    internal SafeFileHandle OpenReadFile(string name)
    {
        var directoryFlag = Mac ? 0x100000
            : RuntimeInformation.ProcessArchitecture == Architecture.Arm64 ? 0x4000 : 0x10000;
        var descriptor = OpenAt(Descriptor, name, (OpenFlags & ~directoryFlag) | (Mac ? 0x4 : 0x800));
        if (descriptor < 0) { throw new InvalidOperationException("OwnershipInvalid"); }
        var result = new SafeFileHandle(descriptor, true);
        try
        {
            var file = ReadIdentity(descriptor);
            if (file.Uid != GetUid() || file.Mode != (0x8000 | 0x100))
            { throw new InvalidOperationException("OwnershipInvalid"); }
            return result;
        }
        catch { result.Dispose(); throw; }
    }

    internal FileStream CreatePrivateFile(string name)
    {
        if (!OperatingSystem.IsLinux()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
        CheckPrivate();
        var directoryFlag = RuntimeInformation.ProcessArchitecture == Architecture.Arm64 ? 0x4000 : 0x10000;
        var flags = (OpenFlags & ~directoryFlag) | 1 | 0x40 | 0x80;
        var descriptor = CreateAt(Descriptor, name, flags, 0x180);
        if (descriptor < 0) { throw new IOException("OwnershipInvalid"); }
        var file = new SafeFileHandle(descriptor, true);
        try { return new FileStream(file, FileAccess.Write); }
        catch { file.Dispose(); throw; }
    }

    internal void VerifyPath(string path)
    {
        CheckPrivate();
        using var current = OpenChain(path);
        current.CheckPrivate();
        if (identity != current.identity) { throw new InvalidOperationException("OwnershipInvalid"); }
    }

    internal void VerifySameDirectory(OwnedDirectoryHandle other)
    {
        CheckPrivate();
        other.CheckPrivate();
        if (identity != other.identity) { throw new InvalidOperationException("OwnershipInvalid"); }
    }

    private void CheckPrivate()
    {
        var current = ReadIdentity(Descriptor);
        if (current != identity || current.Uid != GetUid() || current.Mode != (DirectoryType | 0x1c0))
        { throw new InvalidOperationException("OwnershipInvalid"); }
    }

    private int Descriptor => !IsClosed && !IsInvalid ? handle.ToInt32()
        : throw new ObjectDisposedException(nameof(OwnedDirectoryHandle));
    protected override bool ReleaseHandle() => Close(handle.ToInt32()) == 0;

    private static Identity ReadIdentity(int descriptor)
    {
        var buffer = Marshal.AllocHGlobal(256);
        try
        {
            Marshal.Copy(new byte[256], 0, buffer, 256);
            if (Mac)
            {
                // Darwin arm64/x64 stat64, checked against the descriptor's real file type, uid and mode.
                if (Fstat(descriptor, buffer) != 0) { throw new InvalidOperationException("OwnershipInvalid"); }
                return new((uint)Marshal.ReadInt32(buffer, 0), 0, (ulong)Marshal.ReadInt64(buffer, 8),
                    (uint)Marshal.ReadInt32(buffer, 16), (ushort)Marshal.ReadInt16(buffer, 4));
            }
            // Linux statx is a fixed UAPI layout, unlike architecture-dependent struct stat.
            if (Statx(descriptor, "", 0x1000 | 0x100, 0x7ff, buffer) != 0
                || ((uint)Marshal.ReadInt32(buffer, 0) & 0x10b) != 0x10b)
            { throw new InvalidOperationException("OwnershipInvalid"); }
            return new((uint)Marshal.ReadInt32(buffer, 136), (uint)Marshal.ReadInt32(buffer, 140),
                (ulong)Marshal.ReadInt64(buffer, 32), (uint)Marshal.ReadInt32(buffer, 20),
                (ushort)Marshal.ReadInt16(buffer, 28));
        }
        catch (EntryPointNotFoundException) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private readonly record struct Identity(uint DeviceMajor, uint DeviceMinor, ulong Inode, uint Uid, ushort Mode);

    [DllImport("libc", EntryPoint = "open", SetLastError = true)]
    private static extern int Open(string path, int flags);
    [DllImport("libc", EntryPoint = "openat", SetLastError = true)]
    private static extern int OpenAt(int directory, string path, int flags);
    [DllImport("libc", EntryPoint = "openat", CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
    private static extern int CreateAt(int directory, string path, int flags, int mode);
    [DllImport("libc", EntryPoint = "mkdirat", SetLastError = true)]
    private static extern int MkdirAt(int directory, string path, uint mode);
    [DllImport("libc", EntryPoint = "fstat", SetLastError = true)]
    private static extern int Fstat(int descriptor, IntPtr buffer);
    [DllImport("libc", EntryPoint = "statx", SetLastError = true)]
    private static extern int Statx(int descriptor, string path, int flags, uint mask, IntPtr buffer);
    [DllImport("libc", EntryPoint = "flock", SetLastError = true)]
    private static extern int Flock(int descriptor, int operation);
    [DllImport("libc", EntryPoint = "getuid")]
    private static extern uint GetUid();
    [DllImport("libc", EntryPoint = "close", SetLastError = true)]
    private static extern int Close(int descriptor);
    [DllImport("libc", EntryPoint = "dup", SetLastError = true)]
    private static extern int Dup(int descriptor);
    [DllImport("libc", EntryPoint = "ioctl", SetLastError = true)]
    private static extern int Ioctl(int descriptor, nuint operation);
}
