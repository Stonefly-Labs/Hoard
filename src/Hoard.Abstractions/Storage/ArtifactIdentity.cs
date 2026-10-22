using System.Collections.Immutable;
using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using Hoard.Abstractions.Metadata;

namespace Hoard.Abstractions.Storage;

[DebuggerDisplay("{GetType().Name,nq} (redacted)")]
public abstract record ArtifactDiagnostic
{
    private protected ArtifactDiagnostic() { }
    public sealed override string ToString() => $"{GetType().Name} (redacted)";
}

public abstract record ArtifactOption<T> : ArtifactDiagnostic where T : notnull
{
    private ArtifactOption() { }
    public sealed record None : ArtifactOption<T>;
    public sealed record Some : ArtifactOption<T>
    {
        public Some(T value) => Value = value ?? throw new ArgumentNullException(nameof(value));
        public T Value { get; }
    }
}

public sealed record ArtifactIdentity : ArtifactDiagnostic
{
    public ArtifactIdentity(ArtifactDigest digest, long length, long admittedMaximum = ArtifactLimits.MaximumArtifactBytes)
    {
        ArgumentNullException.ThrowIfNull(digest);
        ArtifactValidation.Require(admittedMaximum is > 0 and <= ArtifactLimits.MaximumArtifactBytes
            && length >= 0 && length <= admittedMaximum);
        Digest = digest;
        Length = length;
    }
    public ArtifactDigest Digest { get; }
    public long Length { get; }
}

public sealed record ArtifactStoreIdentity : ArtifactDiagnostic
{
    public ArtifactStoreIdentity(string providerModuleId, Guid instanceId, Guid epoch)
    {
        ArgumentNullException.ThrowIfNull(providerModuleId);
        ArtifactValidation.Require(Encoding.UTF8.GetByteCount(providerModuleId) is > 0 and <= 128
            && Regex.IsMatch(providerModuleId, @"\A[a-z0-9]+([.-][a-z0-9]+)*\z", RegexOptions.CultureInvariant)
            && instanceId != Guid.Empty && epoch != Guid.Empty);
        ProviderModuleId = providerModuleId;
        InstanceId = instanceId;
        Epoch = epoch;
    }
    public string ProviderModuleId { get; }
    public Guid InstanceId { get; }
    public Guid Epoch { get; }
}

public sealed record ArtifactStamp : ArtifactDiagnostic
{
    public ArtifactStamp(ArtifactStoreIdentity store, ArtifactIdentity identity, Guid incarnation)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArgumentNullException.ThrowIfNull(identity);
        ArtifactValidation.Require(incarnation != Guid.Empty);
        Store = store;
        Identity = identity;
        Incarnation = incarnation;
    }
    public ArtifactStoreIdentity Store { get; }
    public ArtifactIdentity Identity { get; }
    public Guid Incarnation { get; }
}

internal static class ArtifactValidation
{
    public static void Require(bool condition)
    {
        if (!condition) { throw new ArgumentException("Artifact value is outside its supported bound or scope."); }
    }

    public static T Defined<T>(T value) where T : struct, Enum
    {
        Require(Enum.IsDefined(value));
        return value;
    }

    public static Guid Id(Guid value)
    {
        Require(value != Guid.Empty);
        return value;
    }

    public static string Handle(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        Require(value.Length is > 0 and <= 4096 && Encoding.UTF8.GetByteCount(value) <= 4096
            && value.All(character => character is >= '!' and <= '~'));
        return value;
    }

    public static ImmutableArray<T> Collection<T>(IEnumerable<T> values, int maximum) where T : notnull
    {
        ArgumentNullException.ThrowIfNull(values);
        Require(values is not ImmutableArray<T> array || !array.IsDefault);
        var result = values.Take(maximum + 1).ToImmutableArray();
        Require(result.Length <= maximum && result.All(item => item is not null));
        return result;
    }

    public static TimeSpan Duration(TimeSpan value, TimeSpan maximum)
    {
        Require(value >= TimeSpan.FromMilliseconds(1) && value <= maximum);
        return value;
    }
}
