using System.Collections;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Build.Framework;
using static Hoard.Fixtures.Conformance.BuildInputs.Program;

namespace Hoard.Fixtures.Conformance.BuildInputs;

public sealed class CompilerInputsLogger : ILogger
{
    // Keep typed task inputs enabled without diagnostic CLI startup text.
    public LoggerVerbosity Verbosity
    {
        get => LoggerVerbosity.Diagnostic;
        set { }
    }
    public string? Parameters { get; set; } = "";

    private sealed class Compilation(string project)
    {
        internal string Project { get; } = project;
        internal bool Succeeded { get; set; }
        internal string? CommandHash { get; set; }
        internal SortedDictionary<string, string> Sources { get; } = new(StringComparer.Ordinal);
        internal SortedDictionary<string, SortedDictionary<string, string>> Inputs { get; } = new(StringComparer.Ordinal);
        internal SortedDictionary<string, SortedDictionary<string, string>> Metadata { get; } = new(StringComparer.Ordinal);
    }

    private static readonly HashSet<string> FileParameters = new(StringComparer.Ordinal)
    {
        "Sources", "References", "Analyzers", "AdditionalFiles", "AnalyzerConfigFiles", "EmbeddedFiles",
        "Resources", "LinkResources", "ResponseFiles", "Win32Resource", "Win32Manifest",
        "ApplicationConfiguration", "KeyFile", "SourceLink"
    };

    private readonly object gate = new();
    private readonly Dictionary<(int, int, int), Compilation> active = [];
    private readonly List<Compilation> compilations = [];
    private readonly SortedDictionary<string, string> imports = new(StringComparer.Ordinal);
    private readonly SortedDictionary<string, string> frozen = new(StringComparer.Ordinal);
    private readonly SortedSet<string> diagnostics = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> roots = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> expectedSources = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> outputs = new(StringComparer.Ordinal);
    private readonly long started = Stopwatch.GetTimestamp();
    private string requestPath = "";
    private string requestHash = "";
    private string? failure;
    private bool finished;
    private long bytesRead;

    public void Initialize(IEventSource eventSource)
    {
        eventSource.BuildFinished += (_, data) => Finish(data.Succeeded);
        Observe(() =>
        {
            var fields = (Parameters ?? throw new InputException("EvidenceSchemaInvalid")).Split(';');
            Require(fields.Length == 3 && eventSource is IEventSource3, "EvidenceSchemaInvalid");
            var root = new UTF8Encoding(false, true).GetString(Convert.FromBase64String(fields[0]));
            Require(Path.IsPathFullyQualified(root) && Path.GetFullPath(root) == root, "OwnershipInvalid");
            requestPath = OwnedPath(root, fields[1]);
            requestHash = fields[2];
            var bytes = Read(requestPath, MaxManifestBytes);
            Require(HashPattern().IsMatch(requestHash) && Hash(bytes) == requestHash, "InputChanged");
            using var request = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 16 });
            var value = request.RootElement;
            Keys(value, "schemaVersion", "qualification", "sourcePath", "generatedPath", "packagePath",
                "toolchainRoot", "sourceHashes", "outputs");
            Require(value.GetProperty("schemaVersion").GetInt32() == 1
                && value.GetProperty("qualification").ValueKind == JsonValueKind.False, "EvidenceSchemaInvalid");
            Require(Environment.GetEnvironmentVariable("MSBUILDLOGTASKINPUTS") == "1"
                && Environment.GetEnvironmentVariable("MSBUILDLOGIMPORTS") == "1", "PrerequisiteMissing");
            roots.Add("source", OwnedPath(root, Text(value, "sourcePath")));
            roots.Add("generated", OwnedPath(root, Text(value, "generatedPath")));
            roots.Add("packages", OwnedPath(root, Text(value, "packagePath")));
            var toolchain = Directory.GetParent(Path.GetDirectoryName(typeof(ILogger).Assembly.Location)!)?.Parent;
            Require(toolchain is not null && Text(value, "toolchainRoot") == toolchain.FullName, "OwnershipInvalid");
            roots.Add("toolchain", toolchain!.FullName);
            foreach (var (kind, path) in roots)
            {
                foreach (var (otherKind, otherPath) in roots)
                {
                    Require(kind == otherKind || path != otherPath
                        && !path.StartsWith(otherPath + Path.DirectorySeparatorChar, StringComparison.Ordinal),
                        "OwnershipInvalid");
                }
            }

            var sources = value.GetProperty("sourceHashes");
            Require(sources.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
            foreach (var item in sources.EnumerateObject())
            {
                _ = OwnedPath(roots["source"], item.Name);
                var hash = item.Value.GetString();
                Require(hash is not null && HashPattern().IsMatch(hash)
                    && expectedSources.Count < 4096 && expectedSources.TryAdd(item.Name, hash), "EvidenceSchemaInvalid");
            }

            Require(expectedSources.Count > 0, "EvidenceIncomplete");
            var destinations = value.GetProperty("outputs");
            Keys(destinations, "sources", "inputs", "parameters");
            foreach (var property in destinations.EnumerateObject())
            {
                var path = OwnedPath(root, Text(destinations, property.Name));
                Require(!File.Exists(path) && !Directory.Exists(path)
                    && !outputs.ContainsValue(path), "OwnershipInvalid");
                outputs.Add(property.Name, path);
            }

            ((IEventSource3)eventSource).IncludeTaskInputs();
            eventSource.ErrorRaised += (_, data) => Observe(() => Diagnostic(data.Code));
            eventSource.WarningRaised += (_, data) => Observe(() => Diagnostic(data.Code));
            eventSource.TaskStarted += (_, data) => Observe(() =>
            {
                if (data.TaskName != "Csc")
                {
                    return;
                }

                var context = Context(data.BuildEventContext);
                var (identity, _) = FileInput(data.ProjectFile);
                Require(identity.StartsWith("source/", StringComparison.Ordinal)
                    && identity.EndsWith(".csproj", StringComparison.Ordinal)
                    && compilations.Count < 128, "EvidenceIncomplete");
                var compilation = new Compilation(identity["source/".Length..]);
                Require(active.TryAdd(context, compilation), "EvidenceIncomplete");
                compilations.Add(compilation);
            });
            eventSource.TaskFinished += (_, data) => Observe(() =>
            {
                if (data.TaskName == "Csc")
                {
                    Require(active.Remove(Context(data.BuildEventContext), out var compilation), "EvidenceIncomplete");
                    compilation!.Succeeded = data.Succeeded;
                }
            });
            eventSource.AnyEventRaised += (_, data) => Observe(() => Capture(data));
        });
    }

    private void Diagnostic(string? code) =>
        diagnostics.Add(code is not null && Regex.IsMatch(code, @"\A(?:CS|MSB|NU|NETSDK|CA)[0-9]{4}\z")
            ? code : "UnknownDiagnostic");

    private static (int, int, int) Context(BuildEventContext? context)
    {
        Require(context is not null, "EvidenceIncomplete");
        return (context!.NodeId, context.ProjectContextId, context.TaskId);
    }

    private (string Identity, string Hash) FileInput(string name)
    {
        var path = Path.GetFullPath(name);
        var owner = roots.SingleOrDefault(item =>
            path.StartsWith(item.Value + Path.DirectorySeparatorChar, StringComparison.Ordinal));
        Require(owner.Key is not null, "OwnershipInvalid");
        var relative = path[(owner.Value!.Length + 1)..].Replace(Path.DirectorySeparatorChar, '/');
        var identity = owner.Key + "/" + relative;
        Require(owner.Key != "source" || expectedSources.ContainsKey(relative), "EvidenceIncomplete");
        var bytes = Read(OwnedPath(owner.Value, relative),
            (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - bytesRead), allowEmpty: true);
        bytesRead += bytes.Length;
        var hash = Hash(bytes);
        Require(owner.Key != "source" || expectedSources[relative] == hash, "InputChanged");
        if (frozen.TryGetValue(identity, out var previous))
        {
            Require(previous == hash, "InputChanged");
        }
        else
        {
            Require(frozen.Count < 4096, "OutputLimitExceeded");
            frozen.Add(identity, hash);
        }

        return (identity, hash);
    }

    private static string MetadataHash(ITaskItem item)
    {
        var metadata = item.CloneCustomMetadata();
        Require(metadata.Count <= 128, "OutputLimitExceeded");
        var values = new SortedDictionary<string, string>(StringComparer.Ordinal);
        long length = 0;
        foreach (DictionaryEntry entry in metadata)
        {
            Require(entry.Key is string && entry.Value is string, "EvidenceSchemaInvalid");
            var key = (string)entry.Key;
            var value = (string)entry.Value!;
            length += Encoding.UTF8.GetByteCount(key) + Encoding.UTF8.GetByteCount(value);
            Require(length <= 65536 && values.TryAdd(key, value), "OutputLimitExceeded");
        }

        return Hash(JsonSerializer.SerializeToUtf8Bytes(values));
    }

    private void Capture(BuildEventArgs data)
    {
        if (data is ProjectImportedEventArgs import && import.ImportedProjectFile is not null)
        {
            Require(Path.IsPathFullyQualified(import.ImportedProjectFile), "EvidenceIncomplete");
            var (identity, hash) = FileInput(import.ImportedProjectFile);
            imports[identity] = hash;
        }
        if (data is TaskCommandLineEventArgs command
            && active.TryGetValue(Context(command.BuildEventContext), out var compiled))
        {
            Require(compiled.CommandHash is null, "EvidenceIncomplete");
            Require(Encoding.UTF8.GetByteCount(command.CommandLine) <= 1024 * 1024, "OutputLimitExceeded");
            compiled.CommandHash = Hash(Encoding.UTF8.GetBytes(command.CommandLine));
        }
        if (data is not TaskParameterEventArgs parameter || parameter.Kind != TaskParameterMessageKind.TaskInput
            || !FileParameters.Contains(parameter.ItemType)
            || !active.TryGetValue(Context(parameter.BuildEventContext), out var compilation))
        {
            return;
        }

        if (!compilation.Inputs.TryGetValue(parameter.ItemType, out var selected))
        {
            selected = new(StringComparer.Ordinal);
            compilation.Inputs.Add(parameter.ItemType, selected);
            compilation.Metadata.Add(parameter.ItemType, new(StringComparer.Ordinal));
        }
        foreach (var value in parameter.Items)
        {
            Require(value is ITaskItem, "EvidenceSchemaInvalid");
            var item = (ITaskItem)value;
            var (identity, hash) = FileInput(item.GetMetadata("FullPath"));
            Require(selected.Count < 4096 && selected.TryAdd(identity, hash), "EvidenceIncomplete");
            compilation.Metadata[parameter.ItemType].Add(identity, MetadataHash(item));
            if (parameter.ItemType == "Sources")
            {
                compilation.Sources.Add(identity, hash);
            }
        }
    }

    private void Observe(Action operation)
    {
        lock (gate)
        {
            if (failure is not null)
            {
                return;
            }
            try
            {
                Require(Stopwatch.GetElapsedTime(started) < TimeSpan.FromMinutes(10), "DeadlineExceeded");
                operation();
            }
            catch (InputException error)
            {
                failure = error.Message;
            }
            catch
            {
                failure = "UnknownDiagnostic";
            }
        }
    }

    private void Finish(bool succeeded)
    {
        lock (gate)
        {
            if (finished)
            {
                return;
            }
            finished = true;
            Observe(() =>
            {
                Require(succeeded && diagnostics.Count == 0 && active.Count == 0 && compilations.Count > 0
                    && imports.Count > 0
                    && compilations.All(row => row.Succeeded && row.CommandHash is not null
                        && row.Sources.Count > 0 && row.Inputs.TryGetValue("References", out var references)
                        && references.Count > 0), "EvidenceIncomplete");
                foreach (var (identity, expected) in frozen.ToArray())
                {
                    var separator = identity.IndexOf('/');
                    var (observed, hash) = FileInput(Path.Combine(roots[identity[..separator]], identity[(separator + 1)..]));
                    Require(observed == identity && hash == expected, "InputChanged");
                }
                foreach (var (relative, _) in expectedSources)
                {
                    _ = FileInput(OwnedPath(roots["source"], relative));
                }
                Require(Hash(Read(requestPath, MaxManifestBytes)) == requestHash, "InputChanged");
                var receipts = new Dictionary<string, byte[]>
                {
                    ["sources"] = JsonSerializer.SerializeToUtf8Bytes(new
                    {
                        schemaVersion = 1,
                        qualification = false,
                        succeeded = true,
                        compilations = compilations.Select(row => new
                        {
                            project = row.Project,
                            succeeded = row.Succeeded,
                            sources = row.Sources
                        }).ToArray()
                    }),
                    ["inputs"] = JsonSerializer.SerializeToUtf8Bytes(new
                    {
                        schemaVersion = 1,
                        qualification = false,
                        succeeded = true,
                        compilations = compilations.Select(row => new
                        {
                            project = row.Project,
                            succeeded = row.Succeeded,
                            inputs = row.Inputs
                        }).ToArray(),
                        imports,
                        diagnosticCodes = diagnostics,
                        observerErrors = Array.Empty<string>()
                    }),
                    ["parameters"] = JsonSerializer.SerializeToUtf8Bytes(new
                    {
                        schemaVersion = 1,
                        qualification = false,
                        compilations = compilations.Select(row => new
                        {
                            project = row.Project,
                            commandLineSha256 = row.CommandHash,
                            itemMetadata = row.Metadata
                        }).ToArray()
                    })
                };
                Require(receipts.Values.All(bytes => bytes.Length <= MaxManifestBytes), "OutputLimitExceeded");
                foreach (var (kind, bytes) in receipts)
                {
                    using var output = new FileStream(outputs[kind], FileMode.CreateNew, FileAccess.Write, FileShare.None);
                    output.Write(bytes);
                }
            });
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                @event = "control",
                code = failure ?? "None",
                value = failure is null ? compilations.Count : 0
            }));
        }
    }

    public void Shutdown() => Finish(false);
}
