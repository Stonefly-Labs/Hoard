using System.Collections.Immutable;
using System.Diagnostics;

namespace Hoard.Hosting.Configuration;

[DebuggerDisplay("[redacted]")]
public sealed class HoardSecretValue
{
    [DebuggerBrowsable(DebuggerBrowsableState.Never)]
    private string? value;
    internal HoardSecretValue(string value) => this.value = value;
    public string Reveal() => Volatile.Read(ref value) ?? throw new ObjectDisposedException(nameof(HoardSecretValue));
    internal void Release() => Interlocked.Exchange(ref value, null);
    public override string ToString() => "[redacted]";
}

[DebuggerDisplay("Hoard owner options (private)")]
public sealed class HoardModuleOptions
{
    [DebuggerBrowsable(DebuggerBrowsableState.Never)]
    private readonly ImmutableDictionary<string, object> values;
    internal HoardModuleOptions(IEnumerable<KeyValuePair<string, object>> values) =>
        this.values = values.ToImmutableDictionary(StringComparer.Ordinal);
    public bool Contains(string key) => values.ContainsKey(key);
    public string GetString(string key) => Get<string>(key);
    public bool GetBoolean(string key) => Get<bool>(key);
    public long GetInteger(string key) => Get<long>(key);
    public HoardSecretValue GetSecret(string key) => Get<HoardSecretValue>(key);
    private T Get<T>(string key) => values.TryGetValue(key, out var value) && value is T typed ? typed
        : throw new InvalidOperationException("The owner option is absent or has a different declared type.");
    internal void Release()
    {
        foreach (var secret in values.Values.OfType<HoardSecretValue>()) { secret.Release(); }
    }
    public override string ToString() => "Hoard owner options (private)";
}

internal sealed class OwnerOptionsLease(HoardModuleOptions options) : IDisposable
{
    private int released;
    internal HoardModuleOptions Options { get; } = options;
    public void Dispose()
    {
        if (Interlocked.Exchange(ref released, 1) == 0) { Options.Release(); }
    }
}
