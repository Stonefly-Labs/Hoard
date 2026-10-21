using System.Collections.Immutable;
using System.Diagnostics;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Configuration.Conversion;

[DebuggerDisplay("Private configuration conversion session")]
public sealed class HoardConfigurationConversionSession : IAsyncDisposable
{
    private bool approved;
    private bool consumed;
    private bool disposed;
    internal HoardConfigurationConversionSession(HoardBuilder builder, string source, string destination,
        byte[] digest, string proposal, HoardPlatformVersions versions, HoardLifecycleOptions lifecycleOptions,
        HoardConfigurationOptions options, ImmutableArray<ServiceDescriptor> services,
        HoardEnvironmentReader? readEnvironment, HoardConfigurationFileReader? readSecretFile)
    {
        Builder = builder; Source = source; Destination = destination; Digest = digest; Proposal = proposal;
        Versions = versions; LifecycleOptions = lifecycleOptions; Options = options; Services = services;
        ReadEnvironment = readEnvironment; ReadSecretFile = readSecretFile;
    }
    public Guid Identity { get; } = Guid.NewGuid();
    internal HoardBuilder Builder { get; }
    internal string Source { get; }
    internal string Destination { get; }
    internal byte[] Digest { get; }
    internal string Proposal { get; }
    internal HoardPlatformVersions Versions { get; }
    internal HoardLifecycleOptions LifecycleOptions { get; }
    internal HoardConfigurationOptions Options { get; }
    internal ImmutableArray<ServiceDescriptor> Services { get; }
    internal HoardEnvironmentReader? ReadEnvironment { get; }
    internal HoardConfigurationFileReader? ReadSecretFile { get; }
    internal Action<ConfigurationPublicationStage>? PublicationObserver { get; set; }

    public void Approve()
    {
        lock (Builder.ConfigurationGate)
        {
            if (consumed || disposed) { throw new InvalidOperationException("Conversion session is no longer approvable."); }
            approved = true;
        }
    }
    internal bool Consume(HoardBuilder builder)
    {
        lock (Builder.ConfigurationGate)
        {
            if (!approved || consumed || disposed) { return false; }
            consumed = true;
            return ReferenceEquals(builder, Builder) && builder.Services.SequenceEqual(Services);
        }
    }
    public ValueTask DisposeAsync()
    {
        lock (Builder.ConfigurationGate) { disposed = true; }
        return ValueTask.CompletedTask;
    }
    public override string ToString() => "Private configuration conversion session";
}
