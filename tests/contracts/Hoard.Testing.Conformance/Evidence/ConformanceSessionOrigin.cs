using System.Collections.Immutable;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Evidence;

public sealed class ConformanceObservedComponent
{
    internal ConformanceObservedComponent(Guid instanceId, ConformanceLoadedAssembly assembly)
    {
        InstanceId = instanceId;
        Assembly = assembly;
    }

    public Guid InstanceId { get; }
    public ConformanceLoadedAssembly Assembly { get; }
    public override string ToString() => nameof(ConformanceObservedComponent);
}

public sealed class ConformanceSessionOrigin
{
    internal ConformanceSessionOrigin(ConformanceRunContext context, Guid sessionId, Guid? parentSessionId,
        string descriptorSha256, ImmutableSortedDictionary<string, ConformanceObservedComponent> components)
    {
        RunId = context.RunId;
        CaseId = context.CaseId;
        SessionId = sessionId;
        ParentSessionId = parentSessionId;
        DescriptorSha256 = descriptorSha256;
        Components = components;
    }

    public int SchemaVersion => 1;
    public Guid RunId { get; }
    public string CaseId { get; }
    public Guid SessionId { get; }
    public Guid? ParentSessionId { get; }
    public string FactoryOperation => ParentSessionId.HasValue ? "reopen" : "create";
    public string DescriptorSha256 { get; }
    public string RuntimeVersion => Environment.Version.ToString();
    public string ProcessArchitecture => RuntimeInformation.ProcessArchitecture.ToString().ToLowerInvariant();
    public ImmutableSortedDictionary<string, ConformanceObservedComponent> Components { get; }
    public override string ToString() => nameof(ConformanceSessionOrigin);
}

internal sealed class ConformanceSessionOriginTracker(
    IConformanceBinding binding, ConformanceRunContext context, ConformanceBindingDeclaration declaration)
{
    private readonly object gate = new();
    private readonly Dictionary<object, Guid> instances = new(ReferenceEqualityComparer.Instance);
    private readonly ImmutableArray<byte> descriptor = ConformanceBindingSnapshot.Capture(declaration);
    private readonly ImmutableArray<ConformanceFault> declaredFaults = declaration.Faults;

    internal void ValidateFaults(ImmutableArray<ConformanceFault> actual)
    {
        if (actual.IsDefault || actual.Length > 128 || actual.Distinct().Count() != actual.Length
            || actual.Any(fault => !Enum.IsDefined(fault))
            || declaredFaults.Any(fault => !actual.Contains(fault)))
        { throw new ArgumentException("BindingInvalid"); }
    }

    internal ConformanceSessionOrigin Capture(object session, Guid sessionId, Guid? parentSessionId,
        params (string Role, object Component)[] components)
    {
        lock (gate)
        {
            var started = Stopwatch.GetTimestamp();
            if (!descriptor.AsSpan().SequenceEqual(ConformanceBindingSnapshot.Capture(binding.Declaration).AsSpan()))
            { throw new InvalidOperationException("InputChanged"); }
            var result = ImmutableSortedDictionary.CreateBuilder<string, ConformanceObservedComponent>(StringComparer.Ordinal);
            var remainingBytes = 256 * 1024 * 1024;
            Add("factory", binding);
            Add("session", session);
            foreach (var (role, component) in components) { Add(role, component); }
            ConformanceLoadedAssembly.CheckBudget(started);
            return new(context, sessionId, parentSessionId,
                Convert.ToHexStringLower(SHA256.HashData(descriptor.AsSpan())), result.ToImmutable());

            void Add(string role, object component)
            {
                var assembly = ConformanceLoadedAssembly.Capture(component, started, remainingBytes);
                remainingBytes -= assembly.ImageBytes;
                if (!instances.TryGetValue(component, out var instanceId))
                {
                    if (instances.Count >= 1024) { throw new InvalidOperationException("OutputLimitExceeded"); }
                    instanceId = Guid.NewGuid();
                    instances.Add(component, instanceId);
                }
                result.Add(role, new(instanceId, assembly));
            }
        }
    }
}
