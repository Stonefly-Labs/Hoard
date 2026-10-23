using System.Diagnostics;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Evidence;

public sealed class ConformanceLoadedAssembly
{
    private ConformanceLoadedAssembly(string assemblyName, string assemblyVersion, Guid moduleVersionId,
        string assemblySha256, string typeSha256)
    {
        AssemblyName = ConformanceBindingDeclaration.Id(assemblyName);
        AssemblyVersion = ConformanceBindingDeclaration.Id(assemblyVersion);
        ModuleVersionId = moduleVersionId;
        AssemblySha256 = assemblySha256;
        TypeSha256 = typeSha256;
    }

    public string AssemblyName { get; }
    public string AssemblyVersion { get; }
    public Guid ModuleVersionId { get; }
    public string AssemblySha256 { get; }
    public string TypeSha256 { get; }
    public override string ToString() => nameof(ConformanceLoadedAssembly);

    public static ConformanceLoadedAssembly Capture<TContract>(TContract instance) where TContract : class
    {
        ArgumentNullException.ThrowIfNull(instance);
        var started = Stopwatch.GetTimestamp();
        try
        {
            var type = instance.GetType();
            var assembly = type.Assembly;
            if (assembly.IsDynamic || string.IsNullOrEmpty(assembly.Location)
                || type.FullName is not { Length: > 0 and <= 4096 }
                || type.Module != assembly.ManifestModule)
            { throw new InvalidOperationException("ProofMismatch"); }
            var path = assembly.Location;
            CheckLinks(path);
            byte[] bytes;
            using (var source = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                if (!source.CanSeek || source.Length is <= 0 or > 64 * 1024 * 1024)
                { throw new InvalidOperationException("OutputLimitExceeded"); }
                bytes = new byte[(int)source.Length];
                for (var offset = 0; offset < bytes.Length;)
                {
                    CheckBudget(started);
                    var read = source.Read(bytes.AsSpan(offset, Math.Min(64 * 1024, bytes.Length - offset)));
                    if (read == 0) { throw new InvalidOperationException("InputChanged"); }
                    offset += read;
                }
                if (source.ReadByte() != -1 || source.Length != bytes.Length)
                { throw new InvalidOperationException("InputChanged"); }
            }
            CheckLinks(path);
            using var image = new MemoryStream(bytes, writable: false);
            using var reader = new PEReader(image);
            if (!reader.HasMetadata) { throw new InvalidOperationException("ProofMismatch"); }
            var metadata = reader.GetMetadataReader();
            if (!metadata.IsAssembly) { throw new InvalidOperationException("ProofMismatch"); }
            var definition = metadata.GetAssemblyDefinition();
            var moduleId = metadata.GetGuid(metadata.GetModuleDefinition().Mvid);
            var name = assembly.GetName();
            // Inspect the bytes just hashed, never a second read of the assembly path.
            if (moduleId == Guid.Empty || moduleId != type.Module.ModuleVersionId
                || metadata.GetString(definition.Name) != name.Name || definition.Version != name.Version)
            { throw new InvalidOperationException("InputChanged"); }
            var result = new ConformanceLoadedAssembly(name.Name!, definition.Version.ToString(), moduleId,
                Convert.ToHexStringLower(SHA256.HashData(bytes)),
                Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(type.FullName))));
            CheckBudget(started);
            return result;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException
            or BadImageFormatException or NotSupportedException)
        { throw new InvalidOperationException("ProofMismatch"); }
    }

    private static void CheckBudget(long started)
    {
        if (Stopwatch.GetElapsedTime(started) > TimeSpan.FromSeconds(5))
        { throw new InvalidOperationException("DeadlineExceeded"); }
    }

    private static void CheckLinks(string path)
    {
        for (var current = Path.GetFullPath(path); current is not null; current = Path.GetDirectoryName(current))
        {
            if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0
                || new FileInfo(current).LinkTarget is not null)
            { throw new InvalidOperationException("OwnershipInvalid"); }
        }
    }
}
