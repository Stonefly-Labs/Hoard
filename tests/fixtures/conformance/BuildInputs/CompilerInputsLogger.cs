using System.Collections;
using System.Diagnostics;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
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
        internal string? GeneratedDirectory { get; set; }
        internal string? OutputAssembly { get; set; }
        internal string? PdbFile { get; set; }
        internal SortedDictionary<string, object> CompiledOutputs { get; } = new(StringComparer.Ordinal);
        internal SortedDictionary<string, string> GeneratedOutputs { get; } = new(StringComparer.Ordinal);
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
    private readonly SortedDictionary<string, string> tools = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Guid> toolModules = new(StringComparer.Ordinal);
    private readonly SortedDictionary<string, string> supportFiles = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string[]> supportDirectories = new(StringComparer.Ordinal);
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
    private bool compilerSupportCaptured;
    private string? compilerDirectory;
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
                CaptureHostAssemblies();
                CaptureCompilerSupport();
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
                    if (data.Succeeded)
                    {
                        Require(compilation.OutputAssembly is not null, "EvidenceIncomplete");
                        foreach (var (kind, path) in new[]
                        {
                            ("assembly", compilation.OutputAssembly!),
                            ("pdb", compilation.PdbFile ?? Path.ChangeExtension(compilation.OutputAssembly!, ".pdb"))
                        })
                        {
                            var (identity, hash) = FileInput(path);
                            Require(identity.StartsWith("generated/", StringComparison.Ordinal)
                                && identity.EndsWith(kind == "assembly" ? ".dll" : ".pdb", StringComparison.Ordinal),
                                "OwnershipInvalid");
                            compilation.CompiledOutputs.Add(kind, new { path = identity, sha256 = hash });
                        }
                        foreach (var (identity, hash) in CaptureGeneratedOutputs(compilation))
                        {
                            compilation.GeneratedOutputs.Add(identity, hash);
                        }
                    }
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

    private (string Identity, string Hash) FileInput(string name, Guid? moduleId = null)
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
        if (moduleId is not null)
        {
            using var stream = new MemoryStream(bytes, writable: false);
            using var image = new PEReader(stream);
            Require(image.HasMetadata, "ProofMismatch");
            var metadata = image.GetMetadataReader();
            Require(moduleId != Guid.Empty
                && metadata.GetGuid(metadata.GetModuleDefinition().Mvid) == moduleId, "ProofMismatch");
        }
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
        if (data is AssemblyLoadBuildEventArgs assembly)
        {
            Require(assembly.AssemblyPath is not null && Path.IsPathFullyQualified(assembly.AssemblyPath),
                "EvidenceIncomplete");
            CaptureTool(assembly.AssemblyPath!, assembly.MVID);
        }
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
            || !active.TryGetValue(Context(parameter.BuildEventContext), out var compilation))
        {
            return;
        }

        if (parameter.ItemType == "GeneratedFilesOutputPath")
        {
            Require(compilation.GeneratedDirectory is null && parameter.Items.Count == 1
                && parameter.Items[0] is string, "EvidenceIncomplete");
            var path = (string)parameter.Items[0]!;
            Require(Path.IsPathFullyQualified(path), "OwnershipInvalid");
            path = Path.TrimEndingDirectorySeparator(Path.GetFullPath(path));
            Require(path.StartsWith(roots["generated"] + Path.DirectorySeparatorChar, StringComparison.Ordinal),
                "OwnershipInvalid");
            var relative = path[(roots["generated"].Length + 1)..].Replace(Path.DirectorySeparatorChar, '/');
            _ = OwnedPath(roots["generated"], relative);
            Require(compilations.All(row => row.GeneratedDirectory is null
                || row.GeneratedDirectory != path
                && !row.GeneratedDirectory.StartsWith(path + Path.DirectorySeparatorChar, StringComparison.Ordinal)
                && !path.StartsWith(row.GeneratedDirectory + Path.DirectorySeparatorChar, StringComparison.Ordinal)),
                "OwnershipInvalid");
            Require(!Directory.Exists(path) || !Directory.EnumerateFileSystemEntries(path).Any(), "OwnershipInvalid");
            compilation.GeneratedDirectory = path;
            return;
        }
        if (parameter.ItemType is "OutputAssembly" or "PdbFile")
        {
            Require(parameter.Items.Count == 1, "EvidenceIncomplete");
            var value = parameter.Items[0] switch
            {
                ITaskItem item => item.GetMetadata("FullPath"),
                string text when Path.IsPathFullyQualified(text) => text,
                _ => throw new InputException("EvidenceSchemaInvalid")
            };
            Require(Path.IsPathFullyQualified(value), "OwnershipInvalid");
            if (parameter.ItemType == "OutputAssembly")
            {
                Require(compilation.OutputAssembly is null, "EvidenceIncomplete");
                compilation.OutputAssembly = value;
            }
            else
            {
                Require(compilation.PdbFile is null, "EvidenceIncomplete");
                compilation.PdbFile = value;
            }
            return;
        }
        if (parameter.ItemType is "ToolPath" or "ToolExe")
        {
            Require(parameter.Items.Count == 1 && parameter.Items[0] is string, "EvidenceIncomplete");
            var value = (string)parameter.Items[0]!;
            if (parameter.ItemType == "ToolPath")
            {
                Require(value.Length == 0, "OwnershipInvalid");
            }
            else
            {
                Require(value.Length == 0, "OwnershipInvalid");
            }
            return;
        }
        if (!FileParameters.Contains(parameter.ItemType))
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
            if (parameter.ItemType == "Analyzers")
            {
                CaptureSupportDirectory(Path.GetDirectoryName(item.GetMetadata("FullPath"))!);
            }
        }
    }

    private void CaptureCompilerSupport()
    {
        var sdk = Path.GetDirectoryName(typeof(ILogger).Assembly.Location)!;
        Require(toolModules.ContainsKey(Path.Combine(sdk, "Roslyn", "Microsoft.Build.Tasks.CodeAnalysis.dll")),
            "EvidenceIncomplete");
        if (compilerSupportCaptured)
        {
            return;
        }
        var directory = Path.Combine(sdk, "Roslyn", "bincore");
        compilerDirectory = directory;
        Require(!File.Exists(Path.Combine(directory, "csc.runtimeconfig.dev.json")), "OwnershipInvalid");
        CaptureSupportDirectory(Path.GetDirectoryName(typeof(object).Assembly.Location)!);
        CaptureSupportDirectory(Path.Combine(roots["toolchain"], "host", "fxr"));
        foreach (var path in new[]
        {
            Path.Combine(roots["toolchain"], OperatingSystem.IsWindows() ? "dotnet.exe" : "dotnet"),
            Path.Combine(sdk, "MSBuild.deps.json"), Path.Combine(sdk, "MSBuild.runtimeconfig.json")
        })
        {
            var (identity, hash) = FileInput(path);
            supportFiles[identity] = hash;
        }
        var names = new SortedSet<string>(StringComparer.Ordinal) { "csc.deps.json", "csc.runtimeconfig.json" };
        var executable = OperatingSystem.IsWindows() ? "csc.exe" : "csc";
        if (File.Exists(Path.Combine(directory, executable)))
        {
            names.Add(executable);
        }
        var manifestBytes = Read(Path.Combine(directory, "csc.deps.json"), MaxManifestBytes);
        using var manifest = JsonDocument.Parse(manifestBytes,
            new JsonDocumentOptions { MaxDepth = 32 });
        var value = manifest.RootElement;
        Keys(value, "runtimeTarget", "compilationOptions", "targets", "libraries");
        var target = value.GetProperty("targets").GetProperty(Text(value.GetProperty("runtimeTarget"), "name"));
        Require(target.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
        foreach (var library in target.EnumerateObject())
        {
            Require(library.Value.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
            foreach (var assets in library.Value.EnumerateObject())
            {
                Require(assets.Name is "dependencies" or "runtime" or "resources", "EvidenceSchemaInvalid");
                if (assets.Name == "dependencies")
                {
                    continue;
                }
                Require(assets.Value.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
                foreach (var asset in assets.Value.EnumerateObject())
                {
                    Require(names.Count < 4096, "OutputLimitExceeded");
                    _ = OwnedPath(directory, asset.Name);
                    names.Add(asset.Name);
                }
            }
        }
        Require(names.Contains("csc.dll") && names.Contains("Microsoft.CodeAnalysis.CSharp.dll")
            && names.Contains("Microsoft.CodeAnalysis.dll"), "EvidenceIncomplete");
        foreach (var name in names)
        {
            var (identity, hash) = FileInput(OwnedPath(directory, name));
            Require(name != "csc.deps.json" || hash == Hash(manifestBytes), "InputChanged");
            supportFiles[identity] = hash;
        }
        compilerSupportCaptured = true;
    }

    private string[] SupportDirectoryFiles(string directory)
    {
        var owner = roots.SingleOrDefault(item =>
            directory.StartsWith(item.Value + Path.DirectorySeparatorChar, StringComparison.Ordinal));
        Require(owner.Key is not null, "OwnershipInvalid");
        _ = OwnedPath(owner.Value!, directory[(owner.Value!.Length + 1)..].Replace(Path.DirectorySeparatorChar, '/'));
        var pending = new Stack<string>();
        pending.Push(directory);
        var files = new List<string>();
        var entries = 0;
        while (pending.TryPop(out var current))
        {
            foreach (var path in Directory.EnumerateFileSystemEntries(current))
            {
                Require(++entries <= 4096 && Stopwatch.GetElapsedTime(started) < TimeSpan.FromMinutes(10),
                    "OutputLimitExceeded");
                _ = OwnedPath(owner.Value!, path[(owner.Value!.Length + 1)..].Replace(Path.DirectorySeparatorChar, '/'));
                if (Directory.Exists(path))
                {
                    pending.Push(path);
                }
                else
                {
                    files.Add(path);
                }
            }
        }
        Require(files.Count > 0, "EvidenceIncomplete");
        files.Sort(StringComparer.Ordinal);
        return files.ToArray();
    }

    private void CaptureSupportDirectory(string directory)
    {
        directory = Path.GetFullPath(directory);
        if (supportDirectories.ContainsKey(directory))
        {
            return;
        }
        var files = SupportDirectoryFiles(directory);
        Require(supportDirectories.Count < 128, "OutputLimitExceeded");
        supportDirectories.Add(directory, files);
        foreach (var path in files)
        {
            var (identity, hash) = FileInput(path);
            supportFiles[identity] = hash;
        }
    }

    private void CaptureTool(string path, Guid moduleId)
    {
        path = Path.GetFullPath(path);
        if (toolModules.TryGetValue(path, out var previous))
        {
            Require(previous == moduleId, "InputChanged");
            return;
        }
        var (identity, hash) = FileInput(path, moduleId);
        toolModules.Add(path, moduleId);
        tools[identity] = hash;
    }

    private void CaptureHostAssemblies()
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            if (assembly == typeof(CompilerInputsLogger).Assembly)
            {
                continue;
            }
            Require(!assembly.IsDynamic && Path.IsPathFullyQualified(assembly.Location), "EvidenceIncomplete");
            CaptureTool(assembly.Location, assembly.ManifestModule.ModuleVersionId);
        }
    }

    private SortedDictionary<string, string> CaptureGeneratedOutputs(Compilation compilation)
    {
        Require(compilation.GeneratedDirectory is not null, "EvidenceIncomplete");
        var outputs = new SortedDictionary<string, string>(StringComparer.Ordinal);
        var pending = new Stack<string>();
        pending.Push(compilation.GeneratedDirectory!);
        var entries = 0;
        while (pending.TryPop(out var directory))
        {
            if (!Directory.Exists(directory))
            {
                continue;
            }
            foreach (var path in Directory.EnumerateFileSystemEntries(directory))
            {
                Require(++entries <= 4096 && Stopwatch.GetElapsedTime(started) < TimeSpan.FromMinutes(10),
                    "OutputLimitExceeded");
                var relative = path[(roots["generated"].Length + 1)..].Replace(Path.DirectorySeparatorChar, '/');
                _ = OwnedPath(roots["generated"], relative);
                if (Directory.Exists(path))
                {
                    pending.Push(path);
                    continue;
                }
                Require(path.EndsWith(".cs", StringComparison.Ordinal), "EvidenceIncomplete");
                var (identity, hash) = FileInput(path);
                Require(!compilation.Sources.ContainsKey(identity)
                    && outputs.TryAdd(identity, hash), "EvidenceIncomplete");
            }
        }
        return outputs;
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
                CaptureHostAssemblies();
                Require(succeeded && diagnostics.Count == 0 && active.Count == 0 && compilations.Count > 0
                    && imports.Count > 0 && tools.Count > 0
                    && compilations.All(row => row.Succeeded && row.CommandHash is not null
                        && row.Sources.Count > 0 && row.Inputs.TryGetValue("References", out var references)
                        && references.Count > 0), "EvidenceIncomplete");
                foreach (var row in compilations)
                {
                    Require(CaptureGeneratedOutputs(row).SequenceEqual(row.GeneratedOutputs), "InputChanged");
                }
                foreach (var (directory, files) in supportDirectories)
                {
                    Require(SupportDirectoryFiles(directory).SequenceEqual(files), "InputChanged");
                }
                Require(compilerDirectory is not null
                    && !File.Exists(Path.Combine(compilerDirectory, "csc.runtimeconfig.dev.json")), "OwnershipInvalid");
                // Capture and independent revalidation each have the same aggregate byte cap.
                bytesRead = 0;
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
                            sources = row.Sources,
                            generatedOutputs = row.GeneratedOutputs,
                            compiledOutputs = row.CompiledOutputs
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
                        tools,
                        supportFiles,
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
