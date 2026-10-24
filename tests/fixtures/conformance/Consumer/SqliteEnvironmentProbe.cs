using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class SqliteEnvironmentProbe
{
    public static async Task<int> Main(string[] args)
    {
        try
        {
            if (args.Length == 6 && args[0] == "sqlite-native-noncooperation" && OperatingSystem.IsLinux())
            { return await SqliteNativeOwnershipProbe.RunAsync(args); }
            if (args.Length != 5 || args[0] != "sqlite-environment" || !OperatingSystem.IsLinux())
            { throw new InvalidOperationException("PrerequisiteMissing"); }
            var architecture = RuntimeInformation.ProcessArchitecture;
            var rid = architecture switch
            {
                Architecture.X64 => "linux-x64",
                Architecture.Arm64 => "linux-arm64",
                _ => throw new InvalidOperationException("PrerequisiteMissing")
            };
            using var resources = ConformanceResourceAllocator.Open(args[2], args[3]);
            SqliteFixtureConfiguration configuration;
            object nativeLibrary;
            await using (var session = await new SqliteBinding(args[4]).CreateSessionAsync(new(
                Guid.NewGuid(), "sqlite-environment", TimeProvider.System, resources, new ConformanceEvidenceBuffer()), default))
            {
                if (await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default)
                    is not MetadataResult<MetadataSchemaAdmission>.Success)
                { throw new InvalidOperationException("PrerequisiteMissing"); }
                configuration = await ((SqliteMetadataStore)session.Store).ConfigurationForTestAsync() switch
                {
                    MetadataResult<SqliteFixtureConfiguration>.Success success => success.Value,
                    _ => throw new InvalidOperationException("PrerequisiteMissing")
                };
                using var process = Process.GetCurrentProcess();
                var modules = process.Modules;
                if (modules.Count > 4096) { throw new InvalidOperationException("OutputLimitExceeded"); }
                var matching = modules.Cast<ProcessModule>()
                    .Where(module => Path.GetFileName(module.FileName) == "libe_sqlite3.so").ToArray();
                if (matching.Length != 1) { throw new InvalidOperationException("PrerequisiteMissing"); }
                var nativePath = matching[0].FileName;
                var relative = Path.GetRelativePath(AppContext.BaseDirectory, nativePath);
                if (relative != $"runtimes/{rid}/native/libe_sqlite3.so")
                { throw new InvalidOperationException("ProofMismatch"); }
                using var native = new FileStream(nativePath, FileMode.Open, FileAccess.Read, FileShare.Read);
                if (native.Length > 32 * 1024 * 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
                nativeLibrary = new { path = relative, sha256 = Convert.ToHexStringLower(SHA256.HashData(native)) };
            }
            var ledger = resources.ObserveLedger();
            if (ledger.IsEmpty || ledger.Any(entry => entry.Observation.State == ConformanceOwnershipState.Retained)
                || ledger[^1].Observation.State != ConformanceOwnershipState.Settling)
            { throw new InvalidOperationException("CleanupIncomplete"); }
            using var output = new FileStream(args[1], FileMode.CreateNew, FileAccess.Write, FileShare.None);
            JsonSerializer.Serialize(output, new
            {
                schemaVersion = 1,
                runtime = Environment.Version.ToString(),
                architecture = architecture.ToString(),
                nativeSqlite = configuration.NativeVersion,
                pragmas = new
                {
                    journalMode = configuration.JournalMode,
                    synchronous = configuration.Synchronous,
                    foreignKeys = configuration.ForeignKeys,
                    busyTimeout = configuration.BusyTimeout
                },
                nativeLibrary
            });
            return 0;
        }
        catch (Exception error)
        {
            var code = error is InvalidOperationException && error.Message is
                "PrerequisiteMissing" or "ProofMismatch" or "OutputLimitExceeded" or "CleanupIncomplete" or "OwnershipInvalid"
                ? error.Message : "PrerequisiteMissing";
            Console.Error.WriteLine(JsonSerializer.Serialize(new { @event = "control", code, value = 0 }));
            return 2;
        }
    }
}
