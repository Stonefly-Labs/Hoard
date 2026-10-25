using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Hoard.Artifacts.Tests;

internal static class ArtifactSourceCapture
{
    internal static void PublishIfRequested(string identity, params (string Path, byte[] Bytes)[] files)
    {
        var context = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_SOURCE_CONTEXT");
        if (context is not null) { Publish(context, identity, files); }
    }

    internal static void Publish(string contextPath, string identity, params (string Path, byte[] Bytes)[] files)
    {
        var started = Stopwatch.GetTimestamp();
        using var document = JsonDocument.Parse(Read(contextPath, 1024 * 1024));
        var context = document.RootElement;
        Fields(context, "schemaVersion", "runId", "invocationGroupId", "attemptId", "rootId",
            "inputsSha256", "rootPath", "outputDirectory", "cases");
        Assert.Equal(1, context.GetProperty("schemaVersion").GetInt32());
        foreach (var name in new[] { "runId", "invocationGroupId", "attemptId" })
        {
            Assert.True(Guid.TryParseExact(Text(context, name), "D", out var id));
            Assert.NotEqual(Guid.Empty, id);
        }
        Assert.Matches(@"\A[0-9a-f]{32}\z", Text(context, "rootId"));
        Assert.Matches(@"\A[0-9a-f]{64}\z", Text(context, "inputsSha256"));
        var root = Text(context, "rootPath");
        CheckPath(root);
        Assert.NotEqual(Path.GetPathRoot(root), root);
        InsideRoot(contextPath);
        Assert.True(context.GetProperty("cases").ValueKind == JsonValueKind.Object);
        var cases = new Dictionary<string, string[]>(StringComparer.Ordinal);
        foreach (var entry in context.GetProperty("cases").EnumerateObject())
        {
            Assert.InRange(Encoding.UTF8.GetByteCount(entry.Name), 1, 1024);
            Assert.True(entry.Name.All(character => character is >= ' ' and <= '~'));
            var paths = entry.Value.EnumerateArray().Select(value => Assert.IsType<string>(value.GetString())).ToArray();
            Assert.InRange(paths.Length, 1, 3);
            Assert.Equal(paths.Length, paths.Distinct(StringComparer.Ordinal).Count());
            foreach (var path in paths) { InsideRoot(path); }
            Assert.True(cases.TryAdd(entry.Name, paths));
            Assert.InRange(cases.Count, 1, 16);
        }
        Assert.True(cases.TryGetValue(identity, out var selected));
        Assert.NotNull(selected);
        Assert.InRange(files.Length, 1, 3);
        Assert.Equal(selected.Order(StringComparer.Ordinal), files.Select(file => file.Path).Order(StringComparer.Ordinal));
        var consumed = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var file in files)
        {
            InsideRoot(file.Path);
            Assert.InRange(file.Bytes.Length, 0, 16384);
            Assert.Equal(file.Bytes, Read(file.Path, 16384));
            Assert.True(consumed.TryAdd(Hash(Encoding.UTF8.GetBytes(file.Path)), Hash(file.Bytes)));
        }
        var outputDirectory = Text(context, "outputDirectory");
        InsideRoot(outputDirectory);
        Assert.True(Directory.Exists(outputDirectory));
        CheckPath(outputDirectory);
        var packet = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            qualification = false,
            runId = Text(context, "runId"),
            attemptId = Text(context, "attemptId"),
            inputsSha256 = Text(context, "inputsSha256"),
            testIdentity = identity,
            files = consumed
        });
        Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
        using var output = new FileStream(Path.Combine(outputDirectory,
            "artifact-source-" + Hash(Encoding.UTF8.GetBytes(identity)) + ".json"), FileMode.CreateNew, FileAccess.Write);
        output.Write(packet);

        void InsideRoot(string path)
        {
            Assert.True(Path.IsPathFullyQualified(path));
            Assert.Equal(Path.GetFullPath(path), path);
            Assert.StartsWith(root + Path.DirectorySeparatorChar, path, StringComparison.Ordinal);
        }

        void CheckPath(string path)
        {
            Assert.True(Path.IsPathFullyQualified(path));
            Assert.Equal(Path.GetFullPath(path), path);
            var count = 0;
            for (string? current = path; current is not null; current = Path.GetDirectoryName(current))
            {
                Assert.True(++count <= 128);
                Assert.Equal(0, (int)(File.GetAttributes(current) & FileAttributes.ReparsePoint));
            }
            Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
        }

        byte[] Read(string path, int limit)
        {
            CheckPath(path);
            using var source = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            Assert.InRange(source.Length, 0, limit);
            var bytes = new byte[(int)source.Length];
            for (var offset = 0; offset < bytes.Length;)
            {
                var count = Math.Min(65536, bytes.Length - offset);
                source.ReadExactly(bytes.AsSpan(offset, count));
                offset += count;
                Assert.True(Stopwatch.GetElapsedTime(started) <= TimeSpan.FromSeconds(5));
            }
            Assert.Equal(-1, source.ReadByte());
            CheckPath(path);
            return bytes;
        }
    }

    private static void Fields(JsonElement value, params string[] names) =>
        Assert.Equal(names.Order(StringComparer.Ordinal),
            value.EnumerateObject().Select(property => property.Name).Order(StringComparer.Ordinal));

    private static string Text(JsonElement value, string name) => Assert.IsType<string>(value.GetProperty(name).GetString());
    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));
}
