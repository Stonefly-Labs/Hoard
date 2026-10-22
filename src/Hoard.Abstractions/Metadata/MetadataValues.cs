using System.Collections.Immutable;
using System.Diagnostics;
using System.Text;
using System.Text.Json.Serialization;

namespace Hoard.Abstractions.Metadata;

[DebuggerDisplay("{GetType().Name,nq} (redacted)")]
public abstract record MetadataDiagnostic
{
    private protected MetadataDiagnostic() { }
    public sealed override string ToString() => $"{GetType().Name} (redacted)";
}

public sealed record MetadataId : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataId(Guid value)
    {
        if (value == Guid.Empty) { throw new ArgumentException("Metadata identity must be nonempty."); }
        Value = value;
    }
    public Guid Value { get; }
}

public sealed record MetadataRevision : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataRevision(Guid value)
    {
        if (value == Guid.Empty) { throw new ArgumentException("Metadata revision must be nonempty."); }
        Value = value;
    }
    public Guid Value { get; }
}

public sealed record CanonicalText : MetadataDiagnostic
{
    [JsonConstructor]
    public CanonicalText(string value) => Value = MetadataValidation.Text(value, 1, 1024);
    public string Value { get; }
}

public sealed record PublicLabel : MetadataDiagnostic
{
    [JsonConstructor]
    public PublicLabel(string value) => Value = MetadataValidation.Text(value, 0, 512);
    public string Value { get; }
}

public sealed record MetadataInstant : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataInstant(long unixMilliseconds)
    {
        if (unixMilliseconds is < 0 or > 253402300799999) { throw new ArgumentException("Metadata instant is outside the supported range."); }
        UnixMilliseconds = unixMilliseconds;
    }
    public MetadataInstant(DateTimeOffset value) : this(ExactMilliseconds(value)) { }
    public long UnixMilliseconds { get; }
    private static long ExactMilliseconds(DateTimeOffset value)
    {
        if (value.Offset != TimeSpan.Zero || value.Ticks % TimeSpan.TicksPerMillisecond != 0)
        { throw new ArgumentException("Metadata instant must be exact UTC milliseconds."); }
        return value.ToUnixTimeMilliseconds();
    }
}

public sealed record ArtifactDigest : MetadataDiagnostic
{
    [JsonConstructor]
    public ArtifactDigest(string hex)
    {
        ArgumentNullException.ThrowIfNull(hex);
        if (hex.Length != 64 || hex.Any(character => character is not (>= '0' and <= '9' or >= 'a' and <= 'f')))
        { throw new ArgumentException("Artifact digest must be exactly 32 bytes in lowercase hexadecimal."); }
        Hex = hex;
    }
    public ArtifactDigest(ImmutableArray<byte> value) : this(FromBytes(value)) { }
    public string Hex { get; }
    private static string FromBytes(ImmutableArray<byte> value)
    {
        if (value.IsDefault || value.Length != 32) { throw new ArgumentException("Artifact digest must be exactly 32 bytes."); }
        return Convert.ToHexStringLower(value.AsSpan());
    }
}

[JsonConverter(typeof(MetadataOptionConverterFactory))]
public abstract record MetadataOption<T> : MetadataDiagnostic where T : notnull
{
    private MetadataOption() { }
    public sealed record None : MetadataOption<T>;
    public sealed record Some : MetadataOption<T>
    {
        [JsonConstructor]
        public Some(T value) => Value = value ?? throw new ArgumentNullException(nameof(value));
        public T Value { get; }
    }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$expected")]
[JsonDerivedType(typeof(ExpectedRevision.Absent), "absent")]
[JsonDerivedType(typeof(ExpectedRevision.Match), "match")]
public abstract record ExpectedRevision : MetadataDiagnostic
{
    private ExpectedRevision() { }
    public sealed record Absent : ExpectedRevision;
    public sealed record Match(MetadataRevision Revision) : ExpectedRevision;
}

public sealed record MetadataArtifactEvidence : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataArtifactEvidence(string value) => Value = MetadataValidation.Text(value, 1, 16384);
    public string Value { get; }
}

public sealed record MetadataContinuation : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataContinuation(string value) => Value = MetadataValidation.Text(value, 1, 16384);
    public string Value { get; }
}

internal static class MetadataValidation
{
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);

    public static string Text(string value, int minimum, int maximum)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value.Length > maximum) { throw new ArgumentException("Metadata text exceeds its bound."); }
        int count;
        try { count = StrictUtf8.GetByteCount(value); }
        catch (EncoderFallbackException) { throw new ArgumentException("Metadata text must contain valid Unicode."); }
        if (count < minimum || count > maximum || value.EnumerateRunes().Any(Rune.IsControl))
        { throw new ArgumentException("Metadata text has an invalid length or control character."); }
        return value;
    }

    public static ImmutableArray<T> Collection<T>(ImmutableArray<T> values, int minimum, int maximum)
    {
        if (values.IsDefault || values.Length < minimum || values.Length > maximum)
        { throw new ArgumentException("Metadata collection is uninitialized or outside its bound."); }
        return values;
    }

    public static void Require(bool condition)
    {
        if (!condition) { throw new ArgumentException("Invalid metadata structure."); }
    }
}
