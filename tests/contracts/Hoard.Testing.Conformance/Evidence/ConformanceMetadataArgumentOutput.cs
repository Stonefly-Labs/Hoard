using System.Runtime.CompilerServices;
using System.Text.Json;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance.Evidence;

public static class ConformanceMetadataArgumentOutput
{
    public const string Prefix = "hoard-metadata-argument-v1";
    private static readonly ConditionalWeakTable<object, Calls> observed = new();

    internal static void Record(object component, string kind, string value)
    {
        ArgumentNullException.ThrowIfNull(component);
        var role = kind switch
        {
            "continuation-corruption" when value is "Null" or "Omitted" or "WrongType" or "Empty" or "OddHex" or "InvalidHex" => "store",
            "query-corruption" when value is "CacheAuthorization" or "AggregateAuthorization" or "AggregateStart"
                or "AggregateEnd" or "LeaseResource" => "store",
            "lease-expiry" when value is "Renew" or "Release" or "Guard" => "store",
            "schema-layout" when value is "unrelated" or "partial" => "schema",
            _ => throw new ArgumentException("ProofMismatch")
        };
        observed.GetValue(component, _ => new()).Record(new(Guid.NewGuid(), role, kind, value));
    }

    internal static void Flush(ITestOutputHelper output, Guid runId, string caseId, string sourceKind,
        Guid sourceId, string role, object component, Guid instanceId) =>
        observed.GetValue(component, _ => new()).Flush(
            new(output, runId, caseId, sourceKind, sourceId, role, instanceId));

    internal static IDisposable Observe(ITestOutputHelper output, Guid runId, string caseId,
        Guid sourceId, string role, object component, Guid instanceId) =>
        observed.GetValue(component, _ => new()).Observe(
            new(output, runId, caseId, "original-observation", sourceId, role, instanceId));

    private sealed record Call(Guid Id, string Role, string Kind, string Value);

    private sealed record Source(ITestOutputHelper Output, Guid RunId, string CaseId, string SourceKind,
        Guid SourceId, string Role, Guid InstanceId)
    {
        internal void Write(Call call)
        {
            var bytes = JsonSerializer.SerializeToUtf8Bytes(new
            {
                schemaVersion = 1,
                runId = RunId,
                caseId = CaseId,
                callId = call.Id,
                sourceKind = SourceKind,
                sourceId = SourceId,
                componentRole = Role,
                componentInstanceId = InstanceId,
                argumentKind = call.Kind,
                argumentValue = call.Value
            });
            foreach (var packet in ConformanceEvidencePacket.Render(Prefix, call.Id, bytes))
            { Output.WriteLine(packet); }
        }
    }

    private sealed class Receiver(Source source) : IDisposable
    {
        private readonly object gate = new();
        private bool closed;
        private bool writing;
        private int count;

        internal void Write(Call call)
        {
            lock (gate)
            {
                if (closed) { throw new InvalidOperationException("OwnershipInvalid"); }
                if (count >= 128) { throw new InvalidOperationException("OutputLimitExceeded"); }
                count++;
                writing = true;
                try { source.Write(call); }
                finally { writing = false; }
            }
        }

        public void Dispose()
        {
            lock (gate)
            {
                if (writing) { throw new InvalidOperationException("OwnershipInvalid"); }
                closed = true;
            }
        }
    }

    private sealed class Calls
    {
        private readonly object gate = new();
        private readonly List<Call> calls = [];
        private readonly Dictionary<string, Receiver> receivers = new(StringComparer.Ordinal);

        internal void Record(Call call)
        {
            Receiver? receiver;
            lock (gate)
            {
                if (!receivers.TryGetValue(call.Role, out receiver))
                {
                    if (calls.Count >= 128) { throw new InvalidOperationException("OutputLimitExceeded"); }
                    calls.Add(call);
                }
            }
            receiver?.Write(call);
        }

        internal void Flush(Source source)
        {
            Call[] selected;
            lock (gate)
            {
                selected = calls.Where(call => call.Role == source.Role).ToArray();
                if (selected.Length == 0) { return; }
                if (receivers.ContainsKey(source.Role)) { throw new InvalidOperationException("OwnershipInvalid"); }
                calls.RemoveAll(call => call.Role == source.Role);
            }
            foreach (var call in selected) { source.Write(call); }
        }

        internal IDisposable Observe(Source source)
        {
            lock (gate)
            {
                if (receivers.ContainsKey(source.Role) || calls.Any(call => call.Role == source.Role))
                { throw new InvalidOperationException("OwnershipInvalid"); }
                var receiver = new Receiver(source);
                receivers.Add(source.Role, receiver);
                return new Registration(this, source.Role, receiver);
            }
        }

        internal void Remove(string role, Receiver receiver)
        {
            receiver.Dispose();
            lock (gate)
            {
                if (receivers.TryGetValue(role, out var current) && ReferenceEquals(receiver, current))
                { receivers.Remove(role); }
            }
        }
    }

    private sealed class Registration(Calls owner, string role, Receiver receiver) : IDisposable
    {
        private Calls? current = owner;
        public void Dispose() => Interlocked.Exchange(ref current, null)?.Remove(role, receiver);
    }
}
