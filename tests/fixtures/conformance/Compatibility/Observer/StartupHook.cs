using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

internal static class StartupHook
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        RespectNullableAnnotations = true,
        RespectRequiredConstructorParameters = true
    };

    public static void Initialize()
    {
        var root = Path.GetFullPath(Environment.GetEnvironmentVariable("HOARD_COMPATIBILITY_ROOT")
            ?? throw new InvalidOperationException("WitnessMissing"));
        var requestPath = OwnedPath(root, Environment.GetEnvironmentVariable("HOARD_COMPATIBILITY_REQUEST")
            ?? throw new InvalidOperationException("WitnessMissing"));
        using var input = File.OpenRead(requestPath);
        if (input.Length > 1024 * 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
        var request = JsonSerializer.Deserialize<Request>(input, Options)
            ?? throw new InvalidOperationException("WitnessMissing");
        if (request.SchemaVersion != 1 || request.Images.Length is < 3 or > 128
            || request.Required.Length is < 2 or > 32 || request.ExpectedOutput.Length > 32768
            || request.Scenario is not ("registration" or "lifecycle" or "configuration"
                or "metadata-marker" or "artifact-marker" or "memory" or "sqlite" or "local" or "object"))
        { throw new InvalidOperationException("ProofMismatch"); }
        var output = OwnedPath(root, request.OutputPath);
        var standard = Console.Out;
        var captured = new BoundedWriter();
        Console.SetOut(captured);
        Console.SetError(captured);
        AppDomain.CurrentDomain.ProcessExit += (_, _) =>
        {
            var code = "None";
            Loaded[] loaded = [];
            try
            {
                if (Environment.ExitCode != 0) { throw new InvalidOperationException("CommandFailed"); }
                if (captured.Overflow) { throw new InvalidOperationException("OutputLimitExceeded"); }
                var text = captured.Text.Trim();
                var expected = request.ExpectedOutput;
                var matches = expected.StartsWith('{')
                    ? JsonNode.DeepEquals(JsonNode.Parse(expected), JsonNode.Parse(text))
                    : text == expected;
                if (!matches) { throw new InvalidOperationException("UnknownDiagnostic"); }
                loaded = Capture(root, request);
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException
                                         or BadImageFormatException or JsonException or InvalidOperationException)
            {
                code = error is InvalidOperationException && error.Message is
                    ("CommandFailed" or "OutputLimitExceeded" or "ProofMismatch" or "InputChanged" or "UnknownDiagnostic")
                    ? error.Message : "ProofMismatch";
            }
            var proof = new { schemaVersion = 1, qualification = false, request.Scenario, code, loaded };
            using (var destination = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(destination, proof, Options);
            }
            standard.WriteLine(JsonSerializer.Serialize(new { @event = "test", code, value = loaded.Length }, Options));
            standard.Flush();
        };
    }

    private static Loaded[] Capture(string root, Request request)
    {
        var expected = request.Images.ToDictionary(
            image => Path.GetFileNameWithoutExtension(image.Path), StringComparer.Ordinal);
        if (request.Required.Distinct(StringComparer.Ordinal).Count() != request.Required.Length
            || request.Required.Any(name => !expected.ContainsKey(name)))
        { throw new InvalidOperationException("ProofMismatch"); }
        var loaded = new List<Loaded>();
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            if (assembly == typeof(StartupHook).Assembly) { continue; }
            var name = assembly.GetName().Name ?? throw new InvalidOperationException("ProofMismatch");
            if (!expected.TryGetValue(name, out var image))
            {
                if (name.StartsWith("Hoard.", StringComparison.Ordinal))
                { throw new InvalidOperationException("ProofMismatch"); }
                continue;
            }
            var path = OwnedPath(root, image.Path);
            if (assembly.IsDynamic || assembly.Location != path)
            { throw new InvalidOperationException("ProofMismatch"); }
            using var stream = File.OpenRead(path);
            var hash = Convert.ToHexStringLower(SHA256.HashData(stream));
            if (hash != image.Sha256) { throw new InvalidOperationException("InputChanged"); }
            stream.Position = 0;
            using var pe = new PEReader(stream);
            var metadata = pe.GetMetadataReader();
            var mvid = metadata.GetGuid(metadata.GetModuleDefinition().Mvid);
            if (mvid != assembly.ManifestModule.ModuleVersionId
                || metadata.GetString(metadata.GetAssemblyDefinition().Name) != name)
            { throw new InvalidOperationException("ProofMismatch"); }
            loaded.Add(new(name, hash, mvid.ToString("D")));
        }
        if (loaded.Select(image => image.Name).Distinct(StringComparer.Ordinal).Count() != loaded.Count
            || request.Required.Except(loaded.Select(image => image.Name), StringComparer.Ordinal).Any())
        { throw new InvalidOperationException("ProofMismatch"); }
        return [.. loaded.OrderBy(image => image.Name, StringComparer.Ordinal)];
    }

    private static string OwnedPath(string root, string relative)
    {
        if (relative.Length is 0 or > 1024 || Path.IsPathFullyQualified(relative)
            || relative.Contains('\\') || relative.Split('/').Any(part => part is "" or "." or ".."))
        { throw new InvalidOperationException("ProofMismatch"); }
        var path = Path.GetFullPath(Path.Combine(root, relative));
        if (!path.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        { throw new InvalidOperationException("ProofMismatch"); }
        return path;
    }

    private sealed record Image(string Path, string Sha256);
    private sealed record Request(int SchemaVersion, string Scenario, string OutputPath,
        string ExpectedOutput, Image[] Images, string[] Required);
    private sealed record Loaded(string Name, string Sha256, string ModuleVersionId);

    private sealed class BoundedWriter : TextWriter
    {
        private readonly StringBuilder text = new();
        public override Encoding Encoding => Encoding.UTF8;
        public bool Overflow { get; private set; }
        public string Text { get { lock (text) { return text.ToString(); } } }
        public override void Write(char value)
        {
            lock (text)
            {
                if (text.Length == 32768) { Overflow = true; }
                else { text.Append(value); }
            }
        }
    }
}
