using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Hoard.Conformance.TestLogger;

public sealed record RuntimeOwner(int SchemaVersion, Guid RunId, Guid InvocationGroupId, string RootId,
    string RootPathSha256);

public sealed record RuntimeFile(string Id, string Path, string Sha256);

public sealed record RuntimeExpectedTest(string TestIdentity, string FullyQualifiedName, string AssemblyId,
    string PackageId, string BindingId, string MatrixId, string? AssertionSymbol, string CaseId);

public sealed record RuntimeInput(int SchemaVersion, Guid RunId, Guid InvocationGroupId, Guid AttemptId,
    int AttemptSequence, string InputSha256, string RunInputsPath, RuntimeFile[] Assemblies, RuntimeFile[] Packages,
    RuntimeExpectedTest[] Expected, string Purpose);

internal static partial class RuntimeSafety
{
    internal const int MaxManifestBytes = 2 * 1024 * 1024;
    internal const int MaxTests = 10_000;
    internal const long MaxOutputBytes = 8 * 1024 * 1024;
    internal static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 16,
        Converters = { new JsonStringEnumConverter() }
    };

    internal static T Read<T>(string path, string digest)
    {
        var bytes = ReadBytes(path, digest);
        using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 16 });
        CheckKeys(document.RootElement);
        return JsonSerializer.Deserialize<T>(bytes, Json) ?? throw Error();
    }

    internal static void VerifyRunInputs(string path, string digest, Guid runId, Guid groupId)
    {
        var bytes = ReadBytes(path, digest);
        using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 16 });
        CheckKeys(document.RootElement);
        var value = document.RootElement;
        Require(value.GetProperty("schemaVersion").GetInt32() == 1
            && value.GetProperty("runId").GetGuid() == runId
            && value.GetProperty("invocationGroupId").GetGuid() == groupId, "InputChanged");
    }

    private static byte[] ReadBytes(string path, string digest)
    {
        Require(HashPattern().IsMatch(digest));
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Require(stream.Length is > 0 and <= MaxManifestBytes);
        var bytes = new byte[(int)stream.Length];
        stream.ReadExactly(bytes);
        Require(Hash(bytes) == digest, "InputChanged");
        return bytes;
    }

    private static void CheckKeys(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var keys = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                Require(keys.Add(property.Name));
                CheckKeys(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in element.EnumerateArray()) { CheckKeys(item); }
        }
    }

    internal static string Hash(ReadOnlySpan<byte> bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    internal static string FileHash(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Require(stream.Length is > 0 and <= 512 * 1024 * 1024, "OutputLimitExceeded");
        return Convert.ToHexStringLower(SHA256.HashData(stream));
    }

    internal static string OwnedPath(string root, string relative)
    {
        Require(relative is { Length: > 0 and <= 512 }
            && relative.All(c => c is >= ' ' and <= '~')
            && !relative.Contains('\\') && !relative.Contains(':')
            && !Path.IsPathRooted(relative)
            && relative.Split('/').All(part => part is not ("" or "." or "..")), "OwnershipInvalid");
        var path = Path.GetFullPath(Path.Combine(root, relative));
        CheckLinks(path);
        return path;
    }

    internal static void CheckLinks(string path)
    {
        for (var current = Path.GetFullPath(path); current is not null; current = Path.GetDirectoryName(current))
        {
            Require((!File.Exists(current) && !Directory.Exists(current))
                || (File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "OwnershipInvalid");
            Require(new FileInfo(current).LinkTarget is null, "OwnershipInvalid");
        }
    }

    internal static string RootHash(string root) => Hash(Encoding.UTF8.GetBytes(Path.GetFullPath(root)));

    internal static void PrivateRoot(string root)
    {
        CheckLinks(root);
        if (!OperatingSystem.IsWindows())
        {
            const UnixFileMode foreign = UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute
                | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute;
            Require((File.GetUnixFileMode(root) & foreign) == 0, "OwnershipInvalid");
        }
    }

    internal static void Id(string? value) => Require(value is not null && IdPattern().IsMatch(value));
    internal static void Digest(string? value) => Require(value is not null && HashPattern().IsMatch(value));
    internal static void Identity(string? value)
    {
        if (value is null) { throw Error(); }
        Require(value.Length is > 0 and <= 1024
            && value.All(c => char.IsAsciiLetterOrDigit(c) || "_./():, []\"-+".Contains(c)));
        Require(!value.Contains('/') || FrozenSourceIdentity(value));
    }
    private static bool FrozenSourceIdentity(string value)
    {
        const string prefix = "Hoard.Conformance.Tests.CompatibilityBaselineTests."
            + "Compiled_source_provenance_matches_actual_pe_pdb_and_frozen_historical_source";
        return value == prefix + "(variant: \"baseline\", name: \"BinaryContract.dll\", relative: \"Old/Contract.cs\")"
            || value == prefix + "(variant: \"broken\", name: \"BinaryContract.dll\", relative: \"New/Contract.cs\")"
            || value == prefix + "(variant: \"compatible\", name: \"BinaryContract.dll\", relative: \"Old/Contract.cs\")"
            || value == prefix + "(variant: \"consumer\", name: \"RetainedConsumer.dll\", relative: \"Consumer/Program.cs\")";
    }
    internal static void IdentityPair(string identity, string fullyQualifiedName)
    {
        Identity(identity);
        Require(SymbolPattern().IsMatch(fullyQualifiedName)
            && (identity == fullyQualifiedName || (identity.StartsWith(fullyQualifiedName + "(", StringComparison.Ordinal)
                && ParameterPattern().IsMatch(identity[fullyQualifiedName.Length..]))));
    }
    internal static bool AdapterBanner(string text) => AdapterBannerPattern().IsMatch(text);
    internal static string? AdapterMessageBody(string text)
    {
        var match = AdapterMessagePattern().Match(text);
        return match.Success ? match.Groups[1].Value : null;
    }
    internal static void Require([System.Diagnostics.CodeAnalysis.DoesNotReturnIf(false)] bool condition,
        string code = "EvidenceSchemaInvalid")
    {
        if (!condition) { throw Error(code); }
    }
    internal static InvalidDataException Error(string code = "EvidenceSchemaInvalid") => new(code);

    [GeneratedRegex(@"\A[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}\z", RegexOptions.CultureInvariant)]
    private static partial Regex IdPattern();
    [GeneratedRegex(@"\A[0-9a-f]{64}\z", RegexOptions.CultureInvariant)]
    private static partial Regex HashPattern();
    [GeneratedRegex(@"\A[a-zA-Z_][a-zA-Z0-9_.+]*\z", RegexOptions.CultureInvariant)]
    private static partial Regex SymbolPattern();
    [GeneratedRegex("\\A\\([a-zA-Z_][a-zA-Z0-9_]*: (?:\"[a-zA-Z0-9._:/+,()\\[\\]-]{0,128}\"|[-+]?[0-9]+(?:\\.[0-9]+)?|[a-zA-Z_][a-zA-Z0-9_]{0,127})(?:, [a-zA-Z_][a-zA-Z0-9_]*: (?:\"[a-zA-Z0-9._:/+,()\\[\\]-]{0,128}\"|[-+]?[0-9]+(?:\\.[0-9]+)?|[a-zA-Z_][a-zA-Z0-9_]{0,127}))*\\)\\z", RegexOptions.CultureInvariant)]
    private static partial Regex ParameterPattern();
    [GeneratedRegex(@"\AxUnit\.net VSTest Adapter v[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}(?:\+[a-zA-Z0-9.-]{1,64})? \([a-zA-Z0-9 .+-]{1,128}\)\z", RegexOptions.CultureInvariant)]
    private static partial Regex AdapterBannerPattern();
    [GeneratedRegex(@"\A\[xUnit\.net [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{2}\] +([^\r\n]{1,2048})\z", RegexOptions.CultureInvariant)]
    private static partial Regex AdapterMessagePattern();
}
