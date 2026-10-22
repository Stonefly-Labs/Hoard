using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

internal sealed class LocalStateException(ArtifactFailureCode code) : Exception
{
    public ArtifactFailureCode Code { get; } = code;
}

internal sealed class LocalRoot : IDisposable
{
    private static readonly object mountEnumeration = new();
    private readonly FileStream ownership;
    public string Path { get; }
    public LocalState State { get; private set; }

    private LocalRoot(string path, FileStream ownership, LocalState state)
    {
        Path = path;
        this.ownership = ownership;
        State = state;
    }

    public static LocalRoot Open(string configured, ArtifactInitialization request, DateTimeOffset now)
    {
        if (OperatingSystem.IsWindows()) { throw new LocalStateException(ArtifactFailureCode.Unsupported); }
        var path = System.IO.Path.GetFullPath(configured);
        ValidateAncestors(path);
        var exists = Directory.Exists(path);
        if (!exists && request.Mode == ArtifactInitializationMode.ReopenCompatible)
        { throw new LocalStateException(ArtifactFailureCode.IncompatibleStore); }
        if (!Directory.Exists(System.IO.Path.GetDirectoryName(path)))
        { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
        if (!exists) { Directory.CreateDirectory(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
        if ((File.GetUnixFileMode(path) & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute
            | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute)) != 0)
        { throw new LocalStateException(ArtifactFailureCode.AccessDenied); }
        var lockPath = System.IO.Path.Combine(path, ".ownership");
        ValidateFile(lockPath);
        var owner = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        try
        {
            var manifest = System.IO.Path.Combine(path, "local-manifest.json");
            ValidateFile(manifest);
            LocalState state;
            if (request.Mode == ArtifactInitializationMode.CreateEmpty)
            {
                if (Directory.EnumerateFileSystemEntries(path).Any(entry => System.IO.Path.GetFileName(entry) != ".ownership"))
                { throw new LocalStateException(ArtifactFailureCode.IncompatibleStore); }
                state = new LocalState(1, request.Store.ProviderModuleId, request.Store.InstanceId, request.Store.Epoch,
                    Guid.NewGuid(), now, request.Limits);
            }
            else
            {
                state = ReadState(manifest, request.Limits.DecisionBytes);
                if (state.Format != 1 || state.ProviderId != request.Store.ProviderModuleId
                    || state.InstanceId != request.Store.InstanceId || state.Epoch != request.Store.Epoch
                    || state.Limits != request.Limits || state.SessionId == Guid.Empty)
                { throw new LocalStateException(ArtifactFailureCode.IncompatibleStore); }
                state = state with { SessionId = Guid.NewGuid(), TimeFloor = now > state.TimeFloor ? now : state.TimeFloor };
            }
            foreach (var name in new[] { "staging", "data", "decisions", "tickets", "reclamation" })
            {
                var child = System.IO.Path.Combine(path, name);
                ValidateAncestors(child);
                Directory.CreateDirectory(child, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
                if (Volume(child) != Volume(path))
                { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            }
            WriteState(path, state, request.Limits.DecisionBytes);
            return new LocalRoot(path, owner, state);
        }
        catch
        {
            owner.Dispose();
            throw;
        }
    }

    internal static void ValidateAncestors(string path)
    {
        for (var current = new DirectoryInfo(path); current is not null; current = current.Parent)
        {
            if (current.LinkTarget is not null || current.Exists && (current.Attributes & FileAttributes.ReparsePoint) != 0)
            { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            if (current.Exists && !OperatingSystem.IsWindows()
                && (File.GetUnixFileMode(current.FullName) & (UnixFileMode.GroupWrite | UnixFileMode.OtherWrite)) != 0)
            { throw new LocalStateException(ArtifactFailureCode.AccessDenied); }
        }
    }

    internal static void ValidateFile(string path)
    {
        var file = new FileInfo(path);
        if (file.LinkTarget is not null || file.Exists && (file.Attributes & FileAttributes.ReparsePoint) != 0)
        { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
    }

    private static string Volume(string path)
    {
        // macOS mount enumeration uses native shared state; never run it concurrently.
        lock (mountEnumeration)
        {
            return DriveInfo.GetDrives().Select(drive => drive.Name)
                .Where(name => path == name.TrimEnd(System.IO.Path.DirectorySeparatorChar)
                    || path.StartsWith(name.EndsWith(System.IO.Path.DirectorySeparatorChar)
                        ? name : name + System.IO.Path.DirectorySeparatorChar, StringComparison.Ordinal))
                .OrderByDescending(name => name.Length).First();
        }
    }

    private static LocalState ReadState(string path, int maximum)
    {
        if (!File.Exists(path)) { throw new LocalStateException(ArtifactFailureCode.IncompatibleStore); }
        if (new FileInfo(path).Length > maximum) { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
        try
        {
            var envelope = JsonSerializer.Deserialize<LocalEnvelope>(File.ReadAllBytes(path))
                ?? throw new LocalStateException(ArtifactFailureCode.CorruptState);
            var bytes = Convert.FromBase64String(envelope.Payload);
            if (Convert.ToHexStringLower(SHA256.HashData(bytes)) != envelope.Sha256)
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            return JsonSerializer.Deserialize<LocalState>(bytes)
                ?? throw new LocalStateException(ArtifactFailureCode.CorruptState);
        }
        catch (Exception error) when (error is JsonException or FormatException or ArgumentException)
        { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
    }

    private static void WriteState(string root, LocalState state, int maximum)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(state);
        var envelope = JsonSerializer.SerializeToUtf8Bytes(new LocalEnvelope(
            Convert.ToBase64String(payload), Convert.ToHexStringLower(SHA256.HashData(payload))));
        if (envelope.Length > maximum) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
        var pending = System.IO.Path.Combine(root, $".manifest-{Guid.NewGuid():N}");
        using (var output = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
        {
            output.Write(envelope);
            output.Flush(flushToDisk: true);
        }
        File.Move(pending, System.IO.Path.Combine(root, "local-manifest.json"), overwrite: true);
    }

    public void Dispose() => ownership.Dispose();

    public void AdvanceTime(DateTimeOffset now)
    {
        if (now <= State.TimeFloor) { return; }
        State = State with { TimeFloor = now };
    }

    public void PersistTime() => WriteState(Path, State, State.Limits.DecisionBytes);

    public string RecordPath(string area, string key, string extension = ".json")
    {
        var directory = System.IO.Path.Combine(Path, area);
        ValidateAncestors(directory);
        var path = System.IO.Path.Combine(directory, key + extension);
        ValidateFile(path);
        return path;
    }

    public void WriteRecord<T>(string area, string key, T value)
    {
        WriteState(Path, State, State.Limits.DecisionBytes);
        var final = RecordPath(area, key);
        var payload = JsonSerializer.SerializeToUtf8Bytes(value);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new LocalEnvelope(
            Convert.ToBase64String(payload), Convert.ToHexStringLower(SHA256.HashData(payload))));
        if (bytes.Length > State.Limits.DecisionBytes) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
        var pending = RecordPath(area, ".pending-" + Guid.NewGuid().ToString("N"));
        using (var output = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
        {
            output.Write(bytes);
            output.Flush(flushToDisk: true);
        }
        File.Move(pending, final, overwrite: true);
    }

    public IEnumerable<T> ReadRecords<T>(string area, int maximum, Func<T, string> key)
    {
        var directory = System.IO.Path.Combine(Path, area);
        ValidateAncestors(directory);
        var count = 0;
        foreach (var path in Directory.EnumerateFileSystemEntries(directory))
        {
            if (++count > checked(maximum * 2 + 100)) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
            ValidateFile(path);
            var name = System.IO.Path.GetFileName(path);
            if (name.StartsWith(".pending-", StringComparison.Ordinal)) { continue; }
            if (!name.EndsWith(".json", StringComparison.Ordinal) || !File.Exists(path)
                || new FileInfo(path).Length > State.Limits.DecisionBytes)
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            T value;
            try
            {
                var envelope = JsonSerializer.Deserialize<LocalEnvelope>(File.ReadAllBytes(path))
                    ?? throw new LocalStateException(ArtifactFailureCode.CorruptState);
                var bytes = Convert.FromBase64String(envelope.Payload);
                if (Convert.ToHexStringLower(SHA256.HashData(bytes)) != envelope.Sha256)
                { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
                value = JsonSerializer.Deserialize<T>(bytes) ?? throw new LocalStateException(ArtifactFailureCode.CorruptState);
            }
            catch (Exception error) when (error is JsonException or FormatException or ArgumentException)
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            if (!StringComparer.Ordinal.Equals(name, key(value) + ".json"))
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            yield return value;
        }
    }
}
