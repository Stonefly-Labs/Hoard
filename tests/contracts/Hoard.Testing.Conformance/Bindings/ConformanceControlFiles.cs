namespace Hoard.Testing.Conformance.Bindings;

/// <summary>Bounded pinned-directory control I/O; creation requires Linux and is not process ownership proof.</summary>
public sealed class ConformanceControlFiles : IDisposable
{
    private readonly string root;
    private readonly OwnedDirectoryHandle handle;

    public ConformanceControlFiles(string privateRoot)
    {
        root = OwnedDirectoryHandle.Normalize(privateRoot);
        handle = OwnedDirectoryHandle.OpenPrivateParent(root);
    }

    public byte[] Read(string relative, int maxBytes)
    {
        var (directory, name) = Locate(relative, maxBytes);
        using (directory)
        {
            using var stream = new FileStream(directory.OpenReadFile(name), FileAccess.Read);
            var bytes = ReadBounded(stream, maxBytes);
            Verify(directory, relative);
            return bytes;
        }
    }

    internal static byte[] ReadBounded(Stream stream, int maxBytes)
    {
        var length = stream.Length;
        if (length is <= 0 || length > maxBytes)
        { throw new InvalidOperationException("OutputLimitExceeded"); }
        var bytes = new byte[(int)length];
        stream.ReadExactly(bytes);
        if (stream.ReadByte() != -1) { throw new InvalidOperationException("InputChanged"); }
        return bytes;
    }

    public void Write(string relative, ReadOnlySpan<byte> bytes, int maxBytes)
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
        if (bytes.Length == 0 || bytes.Length > maxBytes)
        { throw new InvalidOperationException("OutputLimitExceeded"); }
        var (directory, name) = Locate(relative, maxBytes);
        using (directory)
        {
            using var stream = directory.CreatePrivateFile(name);
            stream.Write(bytes);
            stream.Flush(flushToDisk: true);
            File.SetUnixFileMode(stream.SafeFileHandle, UnixFileMode.UserRead);
            Verify(directory, relative);
        }
    }

    private (OwnedDirectoryHandle Directory, string Name) Locate(string relative, int maxBytes)
    {
        if (maxBytes is <= 0 or > 65536) { throw new ArgumentOutOfRangeException(nameof(maxBytes)); }
        if (relative is not { Length: > 0 and <= 512 } || relative.Any(c => c is < ' ' or > '~')
            || relative.Contains('\\') || relative.Contains(':') || Path.IsPathRooted(relative)
            || relative.Split('/').Any(part => part is "" or "." or ".." or ".git"))
        { throw new InvalidOperationException("OwnershipInvalid"); }
        handle.VerifyPath(root);
        var slash = relative.LastIndexOf('/');
        var parent = slash < 0 ? "" : relative[..slash];
        var directory = handle.OpenRelativeDirectory(parent);
        try
        {
            Verify(directory, relative);
            return (directory, relative[(slash + 1)..]);
        }
        catch { directory.Dispose(); throw; }
    }

    private void Verify(OwnedDirectoryHandle directory, string relative)
    {
        handle.VerifyPath(root);
        directory.VerifyPath(Path.GetDirectoryName(Path.Combine(root, relative))!);
    }

    public void Dispose() => handle.Dispose();
}
