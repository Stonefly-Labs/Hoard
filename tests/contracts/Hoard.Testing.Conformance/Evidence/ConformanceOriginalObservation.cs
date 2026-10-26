using System.Collections.Immutable;
using System.Diagnostics;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Evidence;

public sealed class ConformanceOriginalObservation
{
    private readonly Dictionary<object, Guid> instances;

    private ConformanceOriginalObservation(Guid runId, string caseId, string testIdentity, string bindingId,
        string kind, ConformanceOriginalObservation? parent,
        ImmutableSortedDictionary<string, ConformanceObservedComponent> components,
        Dictionary<object, Guid> instances)
    {
        RunId = runId;
        CaseId = caseId;
        TestIdentity = testIdentity;
        BindingId = bindingId;
        Kind = kind;
        ParentObservationId = parent?.ObservationId;
        Components = components;
        this.instances = instances;
    }

    public Guid RunId { get; }
    public string CaseId { get; }
    public string TestIdentity { get; }
    public string BindingId { get; }
    public string Kind { get; }
    public Guid ObservationId { get; } = Guid.NewGuid();
    public Guid? ParentObservationId { get; }
    public string Operation => Kind == "loaded-contract" ? "contract" : ParentObservationId.HasValue ? "reopen" : "create";
    public ImmutableSortedDictionary<string, ConformanceObservedComponent> Components { get; }
    internal object ComponentObject(string role) =>
        instances.Single(pair => pair.Value == Components[role].InstanceId).Key;
    public override string ToString() => nameof(ConformanceOriginalObservation);

    public static ConformanceOriginalObservation Capture(Guid runId, string caseId, string testIdentity,
        string bindingId, string kind, IReadOnlyCollection<(string Role, object Component)> components,
        ConformanceOriginalObservation? parent = null) =>
        Capture(runId, caseId, testIdentity, bindingId, kind, components, parent, parent);

    public static ConformanceOriginalObservation Capture(Guid runId, string caseId, string testIdentity,
        string bindingId, string kind, IReadOnlyCollection<(string Role, object Component)> components,
        ConformanceOriginalObservation? parent, ConformanceOriginalObservation? previous)
    {
        if (runId == Guid.Empty || testIdentity is not { Length: > 0 and <= 1024 }
            || testIdentity.Any(c => c < ' ' || c > '~'))
        { throw new ArgumentException("ProofMismatch"); }
        ConformanceBindingDeclaration.Id(caseId);
        ConformanceBindingDeclaration.Id(bindingId);
        ArgumentNullException.ThrowIfNull(components);
        string[] roles = kind switch
        {
            "loaded-contract" when parent is null => ["contract"],
            "original-owner" when parent is null && bindingId is "sqlite" or "memory" or "local" or "object" =>
                ["owner"],
            "original-instance" when bindingId is "sqlite" or "memory" =>
                ["owner", "store", "schema", "authority", "controls"],
            "original-instance" when bindingId is "local" or "object" =>
                ["owner", "store", "validator", "maintenance", "lifetime", "authority", "controls"],
            _ => throw new ArgumentException("ProofMismatch")
        };
        if (components.Count != roles.Length
            || !components.Select(component => component.Role).ToHashSet(StringComparer.Ordinal).SetEquals(roles)
            || new[] { parent, previous }.Any(prior => prior is not null
                && (prior.RunId != runId || prior.CaseId != caseId || prior.TestIdentity != testIdentity
                    || prior.BindingId != bindingId || prior.Kind != kind)))
        { throw new ArgumentException("ProofMismatch"); }
        var observed = ImmutableSortedDictionary.CreateBuilder<string, ConformanceObservedComponent>(StringComparer.Ordinal);
        var priorInstances = previous?.instances ?? parent?.instances;
        if (parent is not null && priorInstances is not null
            && parent.instances.Any(pair => !priorInstances.TryGetValue(pair.Key, out var id) || id != pair.Value))
        { throw new ArgumentException("ProofMismatch"); }
        var instances = priorInstances is null ? new Dictionary<object, Guid>(ReferenceEqualityComparer.Instance)
            : new Dictionary<object, Guid>(priorInstances, ReferenceEqualityComparer.Instance);
        var started = Stopwatch.GetTimestamp();
        var remaining = 256 * 1024 * 1024;
        foreach (var (role, component) in components)
        {
            ArgumentNullException.ThrowIfNull(component);
            if (role == "owner" && priorInstances?.ContainsKey(component) == true)
            { throw new ArgumentException("ProofMismatch"); }
            var assembly = kind == "loaded-contract"
                ? ConformanceLoadedAssembly.CaptureType(component as Type
                    ?? throw new ArgumentException("ProofMismatch"), started, remaining)
                : ConformanceLoadedAssembly.Capture(component, started, remaining);
            remaining -= assembly.ImageBytes;
            if (!instances.TryGetValue(component, out var id))
            {
                if (instances.Count >= 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
                instances.Add(component, id = Guid.NewGuid());
            }
            observed.Add(role, new(id, assembly));
        }
        ConformanceLoadedAssembly.CheckBudget(started);
        if (parent is not null && observed["owner"].InstanceId == parent.Components["owner"].InstanceId)
        { throw new ArgumentException("ProofMismatch"); }
        return new(runId, caseId, testIdentity, bindingId, kind, parent, observed.ToImmutable(), instances);
    }
}
