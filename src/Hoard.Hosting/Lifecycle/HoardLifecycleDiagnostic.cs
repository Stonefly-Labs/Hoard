using System.Collections.Immutable;
using System.Text.RegularExpressions;

namespace Hoard.Hosting.Lifecycle;

public sealed record HoardLifecycleDiagnostic
{
    internal HoardLifecycleDiagnostic(string ruleCode, string moduleId, HoardLifecyclePhase phase,
        Guid correlationId, bool cleanup = false, IEnumerable<string>? path = null)
    {
        RuleCode = ruleCode;
        ModuleId = IsSafeId(moduleId) ? moduleId : "registration-unknown";
        Phase = phase;
        CorrelationId = correlationId;
        Cleanup = cleanup;
        CorrectiveAction = ruleCode switch
        {
            "InvalidBudget" => "Supply positive finite lifecycle budgets.",
            "MissingLifecycleAdapter" => "Register one lifecycle adapter for each selected provider.",
            "UnknownSelection" => "Explicitly register and select an included module.",
            "DependencyCycle" => "Remove the involved active dependency cycle.",
            "UnsupportedPlatform" or "UnsupportedDependency" or "UnsupportedCapability" =>
                "Install compatible versions or explicitly correct the selection and revalidate.",
            "InvalidCardinality" => "Select exactly one authoritative metadata and artifact module.",
            "AmbiguousRoute" or "UnsupportedRouteShape" or "MissingEndpoint" =>
                "Correct owned routes and responsibilities within the supported route language.",
            "InvalidReadiness" or "NotReady" => "Correct the selected module readiness and declared observations.",
            "StaleComposition" => "Validate the current builder inputs and create a fresh lifecycle.",
            "Timeout" or "UnsafePendingCallback" or "LateCallbackFailure" => "Inspect trusted module cooperation; terminate and restart the process if resources remain in use.",
            "Cancelled" or "TerminalLifecycle" => "Create a fresh validated lifecycle; stopped or failed instances cannot restart.",
            "CancellationFailure" => "Correct trusted module cancellation callbacks for the named phase before starting a fresh lifecycle.",
            "IndependentWorker" => "Use the lifecycle RunAsync callback instead of independent hosted services.",
            _ => "Correct the named composition or lifecycle rule and start a fresh validated instance."
        };
        var ids = (path ?? []).Select(id => IsSafeId(id) ? id : "registration-unknown").ToArray();
        DependencyPath = ids.Take(32).ToImmutableArray();
        OmittedPathCount = Math.Max(0, ids.Length - 32);
    }

    public string RuleCode { get; }
    public string ModuleId { get; }
    public HoardLifecyclePhase Phase { get; }
    public ImmutableArray<string> DependencyPath { get; }
    public int OmittedPathCount { get; }
    public string CorrectiveAction { get; }
    public Guid CorrelationId { get; }
    public bool Cleanup { get; }

    internal static bool IsSafeId(string? id) => id is { Length: > 0 and <= 128 }
        && Regex.IsMatch(id, @"\A[a-z0-9]+([.-][a-z0-9]+)*\z",
            RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1));
}
