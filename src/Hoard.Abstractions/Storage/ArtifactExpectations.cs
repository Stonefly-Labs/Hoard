using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Abstractions.Storage;

public sealed record ArtifactChecksumExpectation : ArtifactDiagnostic
{
    public ArtifactChecksumExpectation(string algorithm, IEnumerable<byte> digest)
    {
        ArgumentNullException.ThrowIfNull(algorithm);
        ArtifactValidation.Require(algorithm.Length is >= 1 and <= 16
            && algorithm.All(character => character is >= '!' and <= '~'));
        Algorithm = algorithm;
        Digest = ArtifactValidation.Collection(digest, 64);
        ArtifactValidation.Require(Digest.Length > 0);
    }
    public string Algorithm { get; }
    public ImmutableArray<byte> Digest { get; }
}

public sealed record ArtifactExpectations : ArtifactDiagnostic
{
    public ArtifactExpectations(long byteCap, ArtifactOption<ArtifactDigest>? sha256 = null,
        ArtifactOption<long>? exactLength = null,
        ArtifactOption<ArtifactChecksumExpectation>? checksum = null)
    {
        ArtifactValidation.Require(byteCap is > 0 and <= ArtifactLimits.MaximumArtifactBytes);
        ByteCap = byteCap;
        Sha256 = sha256 ?? new ArtifactOption<ArtifactDigest>.None();
        ExactLength = exactLength ?? new ArtifactOption<long>.None();
        Checksum = checksum ?? new ArtifactOption<ArtifactChecksumExpectation>.None();
        ArtifactValidation.Require(ExactLength is not ArtifactOption<long>.Some length
            || (length.Value >= 0 && length.Value <= byteCap));
    }
    public long ByteCap { get; }
    public ArtifactOption<ArtifactDigest> Sha256 { get; }
    public ArtifactOption<long> ExactLength { get; }
    public ArtifactOption<ArtifactChecksumExpectation> Checksum { get; }
}
