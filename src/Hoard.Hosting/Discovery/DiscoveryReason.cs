namespace Hoard.Hosting.Discovery;

public sealed record DiscoveryReason
{
    internal DiscoveryReason(string code, string? moduleId = null, string? operationId = null, Guid? correlationId = null)
    {
        Code = Actions.ContainsKey(code) ? code : "observation-unavailable";
        CorrectiveAction = Actions[Code];
        ModuleId = moduleId;
        OperationId = operationId;
        CorrelationId = correlationId;
    }

    public string Code { get; }
    public string CorrectiveAction { get; }
    public string? ModuleId { get; }
    public string? OperationId { get; }
    public Guid? CorrelationId { get; }

    private static readonly IReadOnlyDictionary<string, string> Actions = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["missing-inclusion"] = "Inspect the distribution records; add the package, rebuild, redeploy and restart if needed.",
        ["missing-registration"] = "Register the included module in a custom host, rebuild, redeploy and restart.",
        ["disabled"] = "Change the validated bundled selection and explicitly restart if this module is needed.",
        ["unsupported"] = "Use an implemented and tested operation supported by this distribution.",
        ["unverified"] = "Obtain explicit implemented-and-tested distribution evidence before relying on this operation.",
        ["dependency-unavailable"] = "Correct the required module selection or integration and explicitly restart.",
        ["binding-unavailable"] = "Correct the owned operation binding, rebuild the host and restart.",
        ["initializing"] = "Wait for initialization and inspect a fresh observation.",
        ["not-ready"] = "Investigate the selected module configuration and runtime readiness.",
        ["stopping"] = "Wait for shutdown; start a fresh validated lifecycle before using operations.",
        ["stopped"] = "Start a fresh validated lifecycle; stopped instances cannot restart.",
        ["observation-unknown"] = "Inspect the known distribution and obtain a compatible current observation.",
        ["metadata-suppressed"] = "Review and explicitly approve safe public descriptive metadata in the host catalog.",
        ["observation-unavailable"] = "Inspect safe local lifecycle diagnostics and retry a current authorized read.",
        ["deadline"] = "Inspect the bounded observation workload and retry within the configured finite budget.",
        ["response-limit"] = "Reduce the explicit public catalog to the documented response bounds and restart.",
        ["invalid-protection"] = "Configure and verify the explicit management-read and transport posture before inspection.",
        ["invalid-request"] = "Use the documented literal GET route without query parameters.",
        ["unauthenticated"] = "Authenticate using the host's documented management integration.",
        ["forbidden"] = "Obtain management-read permission through the host's documented access policy.",
        ["cancelled"] = "Retry inspection with an active request cancellation token."
    };
}
