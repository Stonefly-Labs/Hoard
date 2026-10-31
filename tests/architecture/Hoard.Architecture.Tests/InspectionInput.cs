using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using Mono.Cecil;

namespace Hoard.Architecture.Tests;

internal static class InspectionInput
{
    private const int MaxFiles = 2048;
    private const int MaxFileBytes = 64 * 1024 * 1024;
    private const int MaxTotalBytes = 256 * 1024 * 1024;
    private static readonly AsyncLocal<Capture?> Current = new();

    internal static Capture Begin(Guid runId, Guid attemptId, string identity, string inputsSha256,
        IReadOnlyDictionary<string, string> expected, string outputDirectory)
    {
        if (Current.Value is not null) { throw new InspectionException("ProofMismatch"); }
        var capture = new Capture(runId, attemptId, identity, inputsSha256, expected, outputDirectory);
        Current.Value = capture;
        return capture;
    }

    internal static Capture? BeginIfRequested(string identity)
    {
        var path = Environment.GetEnvironmentVariable("HOARD_INSPECTION_CONTEXT");
        if (path is null) { return null; }
        try
        {
            return BeginFromContext(identity, ReadFile(path, 1024 * 1024));
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or ArgumentException)
        {
            throw new InspectionException("ProofMismatch");
        }
    }

    internal static Capture BeginFromContext(string identity, byte[] data)
    {
        if (data.Length > 1024 * 1024) { throw new InspectionException("OutputLimitExceeded"); }
        try
        {
            using var context = JsonDocument.Parse(data);
            var root = context.RootElement;
            Fields(root, "schemaVersion", "runId", "attemptId", "inputsSha256", "outputDirectory", "cases");
            if (root.GetProperty("schemaVersion").GetInt32() != 1) { throw new InspectionException("ProofMismatch"); }
            var cases = root.GetProperty("cases");
            if (cases.ValueKind != JsonValueKind.Object) { throw new InspectionException("ProofMismatch"); }
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in cases.EnumerateObject())
            {
                if (!names.Add(item.Name) || names.Count > 6 || item.Value.ValueKind != JsonValueKind.Object)
                { throw new InspectionException("ProofMismatch"); }
                var paths = new HashSet<string>(StringComparer.Ordinal);
                foreach (var file in item.Value.EnumerateObject())
                {
                    if (!paths.Add(file.Name) || paths.Count > MaxFiles || file.Value.ValueKind != JsonValueKind.String
                        || !IsHash(file.Value.GetString()) || !Path.IsPathFullyQualified(file.Name)
                        || file.Name.Length > 4096 || Path.GetFullPath(file.Name) != file.Name)
                    { throw new InspectionException("ProofMismatch"); }
                }
            }
            if (!cases.TryGetProperty(identity, out var files) || files.ValueKind != JsonValueKind.Object)
            { throw new InspectionException("ProofMismatch"); }
            var expected = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var file in files.EnumerateObject())
            {
                if (expected.Count >= MaxFiles || !expected.TryAdd(file.Name, file.Value.GetString()!))
                { throw new InspectionException("ProofMismatch"); }
            }
            return Begin(root.GetProperty("runId").GetGuid(), root.GetProperty("attemptId").GetGuid(),
                identity, root.GetProperty("inputsSha256").GetString()!, expected,
                root.GetProperty("outputDirectory").GetString()!);
        }
        catch (Exception error) when (error is JsonException or ArgumentException or InvalidOperationException or FormatException)
        {
            throw new InspectionException("ProofMismatch");
        }
    }

    internal static string ReadAllText(string path)
    {
        if (Current.Value is not { } capture) { return File.ReadAllText(path); }
        using var reader = new StreamReader(new MemoryStream(capture.Read(path), writable: false), Encoding.UTF8,
            detectEncodingFromByteOrderMarks: true);
        return reader.ReadToEnd();
    }

    internal static XDocument LoadXml(string path)
    {
        if (Current.Value is not { } capture) { return XDocument.Load(path); }
        using var input = new MemoryStream(capture.Read(path), writable: false);
        return XDocument.Load(input);
    }

    internal static AssemblyDefinition ReadAssembly(string path)
        => Current.Value is { } capture
            ? AssemblyDefinition.ReadAssembly(new MemoryStream(capture.Read(path), writable: false))
            : AssemblyDefinition.ReadAssembly(path);

    private static void Fields(JsonElement value, params string[] expected)
    {
        if (value.ValueKind != JsonValueKind.Object) { throw new InspectionException("ProofMismatch"); }
        var actual = value.EnumerateObject().Select(item => item.Name).ToArray();
        if (actual.Length != expected.Length || !actual.Order().SequenceEqual(expected.Order()))
        { throw new InspectionException("ProofMismatch"); }
    }

    private static bool IsHash(string? value)
        => value is { Length: 64 } && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private static void RegularFile(string path)
    {
        if ((File.GetAttributes(path) & (FileAttributes.Directory | FileAttributes.ReparsePoint)) != 0)
        { throw new InspectionException("ProofMismatch"); }
    }

    private static byte[] ReadFile(string path, int limit)
    {
        var started = Stopwatch.GetTimestamp();
        RegularFile(path);
        using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (input.Length > limit) { throw new InspectionException("OutputLimitExceeded"); }
        var bytes = new byte[checked((int)input.Length)];
        var offset = 0;
        while (offset < bytes.Length)
        {
            if (Stopwatch.GetElapsedTime(started) > TimeSpan.FromSeconds(5))
            { throw new InspectionException("DeadlineExceeded"); }
            var count = input.Read(bytes, offset, Math.Min(64 * 1024, bytes.Length - offset));
            if (count == 0) { throw new InspectionException("InputChanged"); }
            offset += count;
        }
        if (input.ReadByte() != -1 || input.Length != bytes.Length) { throw new InspectionException("InputChanged"); }
        if (Stopwatch.GetElapsedTime(started) > TimeSpan.FromSeconds(5))
        { throw new InspectionException("DeadlineExceeded"); }
        return bytes;
    }

    internal sealed class Capture : IDisposable
    {
        private readonly Guid runId;
        private readonly Guid attemptId;
        private readonly string identity;
        private readonly string inputsSha256;
        private readonly string outputDirectory;
        private readonly Dictionary<string, string> expected = new(StringComparer.Ordinal);
        private readonly Dictionary<string, byte[]> snapshots = new(StringComparer.Ordinal);
        private int totalBytes;
        private bool completed;
        private bool failed;
        private bool disposed;

        internal Capture(Guid runId, Guid attemptId, string identity, string inputsSha256,
            IReadOnlyDictionary<string, string> expected, string outputDirectory)
        {
            if (runId == Guid.Empty || attemptId == Guid.Empty || !IsHash(inputsSha256)
                || string.IsNullOrEmpty(identity) || identity.Length > 512
                || identity.Any(character => !(character is >= 'a' and <= 'z' or >= 'A' and <= 'Z'
                    or >= '0' and <= '9' or '_' or '.'))
                || expected.Count > MaxFiles || string.IsNullOrEmpty(outputDirectory)
                || !Path.IsPathFullyQualified(outputDirectory) || Path.GetFullPath(outputDirectory) != outputDirectory)
            { throw new InspectionException("ProofMismatch"); }
            foreach (var file in expected)
            {
                if (!Path.IsPathFullyQualified(file.Key) || file.Key.Length > 4096
                    || Path.GetFullPath(file.Key) != file.Key || !IsHash(file.Value))
                { throw new InspectionException("ProofMismatch"); }
                this.expected.Add(file.Key, file.Value);
            }
            this.runId = runId;
            this.attemptId = attemptId;
            this.identity = identity;
            this.inputsSha256 = inputsSha256;
            this.outputDirectory = outputDirectory;
        }

        internal byte[] Read(string path)
        {
            CheckActive();
            try
            {
                if (!expected.TryGetValue(path, out var hash)) { throw new InspectionException("ProofMismatch"); }
                if (snapshots.TryGetValue(path, out var selected)) { return selected; }
                var bytes = ReadFile(path, Math.Min(MaxFileBytes, MaxTotalBytes - totalBytes));
                if (Hash(bytes) != hash) { throw new InspectionException("InputChanged"); }
                snapshots.Add(path, bytes);
                totalBytes += bytes.Length;
                return bytes;
            }
            catch (InspectionException) { failed = true; throw; }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException or ArgumentException)
            {
                failed = true;
                throw new InspectionException("ProofMismatch");
            }
        }

        internal void Complete()
        {
            CheckActive();
            try
            {
                if (snapshots.Count != expected.Count) { throw new InspectionException("EvidenceIncomplete"); }
                foreach (var file in expected)
                {
                    if (Hash(ReadFile(file.Key, MaxFileBytes)) != file.Value)
                    { throw new InspectionException("InputChanged"); }
                }
                if ((File.GetAttributes(outputDirectory) & (FileAttributes.Directory | FileAttributes.ReparsePoint))
                    != FileAttributes.Directory)
                { throw new InspectionException("ProofMismatch"); }
                var files = expected.ToDictionary(file => Hash(Encoding.UTF8.GetBytes(file.Key)), file => file.Value);
                var bytes = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    schemaVersion = 1,
                    qualification = false,
                    runId,
                    attemptId,
                    testIdentity = identity,
                    inputsSha256,
                    files
                });
                if (bytes.Length > 512 * 1024) { throw new InspectionException("OutputLimitExceeded"); }
                var name = "inspection-" + Hash(Encoding.UTF8.GetBytes(identity)) + ".json";
                using var output = new FileStream(Path.Combine(outputDirectory, name), FileMode.CreateNew,
                    FileAccess.Write, FileShare.None);
                output.Write(bytes);
                output.Flush(flushToDisk: true);
                completed = true;
            }
            catch (InspectionException) { failed = true; throw; }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException or ArgumentException)
            {
                failed = true;
                throw new InspectionException("ProofMismatch");
            }
        }

        private void CheckActive()
        {
            if (completed || failed || disposed || !ReferenceEquals(Current.Value, this))
            { throw new InspectionException("EvidenceIncomplete"); }
        }

        public void Dispose()
        {
            if (disposed) { return; }
            disposed = true;
            snapshots.Clear();
            if (!ReferenceEquals(Current.Value, this)) { throw new InspectionException("ProofMismatch"); }
            Current.Value = null;
        }
    }
}
