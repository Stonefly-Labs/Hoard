using System.Collections.Immutable;
using System.Text.RegularExpressions;

namespace Hoard.Testing.Conformance.Bindings;

public enum ConformanceCategory { Metadata, Artifacts }

public enum ConformanceFault
{
    IndependentSnapshot, WriterContention, CommitAcknowledgement, PersistedCorruption,
    Capacity, SchemaState, LeaseBoundary, BackupRestore, PublicationBoundary,
    PayloadDamage, NativeNonCooperation, CleanupFailure, GenerationBoundary,
    ReceiptBoundary, SourceNonCooperation, SinkNonCooperation, DirectVisibility
}

public sealed partial class ConformanceBindingDeclaration
{
    public ConformanceBindingDeclaration(string bindingId, ConformanceCategory category,
        string packageId, string packageVersion, string packageSha256,
        IEnumerable<string> capabilities, IEnumerable<ConformanceFault> faults)
    {
        BindingId = Id(bindingId);
        if (!Enum.IsDefined(category)) { throw new ArgumentException("BindingInvalid"); }
        Category = category;
        PackageId = Id(packageId);
        PackageVersion = Id(packageVersion);
        if (!DigestPattern().IsMatch(packageSha256)) { throw new ArgumentException("BindingInvalid"); }
        PackageSha256 = packageSha256;
        ArgumentNullException.ThrowIfNull(capabilities);
        ArgumentNullException.ThrowIfNull(faults);
        Capabilities = capabilities.Take(129).Select(Id).ToImmutableArray();
        Faults = faults.Take(129).ToImmutableArray();
        if (Capabilities.Length is 0 or > 128 || Capabilities.Distinct(StringComparer.Ordinal).Count() != Capabilities.Length
            || Faults.Length is 0 or > 128 || Faults.Distinct().Count() != Faults.Length
            || Faults.Any(fault => !Enum.IsDefined(fault)))
        { throw new ArgumentException("BindingInvalid"); }
    }

    public string BindingId { get; }
    public ConformanceCategory Category { get; }
    public string PackageId { get; }
    public string PackageVersion { get; }
    public string PackageSha256 { get; }
    public ImmutableArray<string> Capabilities { get; }
    public ImmutableArray<ConformanceFault> Faults { get; }
    public override string ToString() => BindingId;

    public static string Id(string value)
    {
        if (value is null || !IdPattern().IsMatch(value)) { throw new ArgumentException("BindingInvalid"); }
        return value;
    }

    [GeneratedRegex(@"\A[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}\z", RegexOptions.CultureInvariant)]
    private static partial Regex IdPattern();
    [GeneratedRegex(@"\A[0-9a-f]{64}\z", RegexOptions.CultureInvariant)]
    private static partial Regex DigestPattern();
}

public interface IConformanceBinding
{
    ConformanceBindingDeclaration Declaration { get; }
}

public interface IMetadataConformanceBinding : IConformanceBinding
{
    ValueTask<IMetadataConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken);
}

public interface IArtifactConformanceBinding : IConformanceBinding
{
    ValueTask<IArtifactConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken cancellationToken);
}

public static class ConformanceBindingAdmission
{
    public static ImmutableArray<ConformanceFault> RequiredFaults(ConformanceCategory category) => category switch
    {
        ConformanceCategory.Metadata => [
            ConformanceFault.IndependentSnapshot, ConformanceFault.WriterContention,
            ConformanceFault.CommitAcknowledgement, ConformanceFault.PersistedCorruption,
            ConformanceFault.Capacity, ConformanceFault.SchemaState, ConformanceFault.LeaseBoundary,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure],
        ConformanceCategory.Artifacts => [
            ConformanceFault.PublicationBoundary, ConformanceFault.DirectVisibility,
            ConformanceFault.PayloadDamage, ConformanceFault.Capacity,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure,
            ConformanceFault.GenerationBoundary, ConformanceFault.ReceiptBoundary,
            ConformanceFault.SourceNonCooperation, ConformanceFault.SinkNonCooperation],
        _ => throw new ArgumentException("BindingInvalid")
    };

    public static void Validate(ConformanceBindingDeclaration declaration, ConformanceCategory category)
    {
        ArgumentNullException.ThrowIfNull(declaration);
        if (declaration.Category != category
            || RequiredFaults(category).Any(fault => !declaration.Faults.Contains(fault))
            || (declaration.Capabilities.Contains("durable-local-process-crash", StringComparer.Ordinal)
                && category == ConformanceCategory.Metadata && !declaration.Faults.Contains(ConformanceFault.BackupRestore)))
        { throw new ArgumentException("BindingInvalid"); }
    }
}
