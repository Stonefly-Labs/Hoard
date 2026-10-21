using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration;

public delegate ValueTask<HoardOptionCheckResult> HoardOptionValidator(
    HoardOptionCheckContext context, CancellationToken cancellationToken);

public enum HoardOptionCheckPhase { Public, Secrets }

public sealed record HoardOptionViolation(string Field, string Rule);

public sealed class HoardOptionCheckResult
{
    public HoardOptionCheckResult(IEnumerable<HoardOptionViolation> violations) =>
        Violations = violations.Take(257).ToImmutableArray();
    public ImmutableArray<HoardOptionViolation> Violations { get; }
    public static HoardOptionCheckResult Accepted { get; } = new([]);
}

public sealed class HoardOptionCheckContext
{
    internal HoardOptionCheckContext(HoardOptionCheckPhase phase, HoardModuleOptions options,
        IEnumerable<string> references)
    { Phase = phase; Options = options; this.references = references.ToImmutableHashSet(StringComparer.Ordinal); }
    private readonly ImmutableHashSet<string> references;
    public HoardOptionCheckPhase Phase { get; }
    public HoardModuleOptions Options { get; }
    public bool HasSecretReference(string key) => references.Contains(key);
    public override string ToString() => $"Hoard option check ({Phase})";
}
