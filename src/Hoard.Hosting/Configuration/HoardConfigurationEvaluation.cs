using System.Collections.Immutable;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Configuration;

public sealed class HoardConfigurationEvaluation : IAsyncDisposable
{
    private readonly ConfigurationSupervisor? supervisor;
    internal HoardConfigurationEvaluation(HoardConfigurationOutcome outcome, HoardConfigurationReport report,
        ConfigurationSupervisor? supervisor = null, HoardValidatedConfiguration? configuration = null)
    { Outcome = outcome; Report = report; this.supervisor = supervisor; Configuration = configuration; }
    public HoardConfigurationOutcome Outcome { get; }
    public HoardConfigurationReport Report { get; }
    public HoardValidatedConfiguration? Configuration { get; }
    public HoardConfigurationSupervision Supervision => supervisor?.Snapshot ?? new(0, [], 0);
    public async ValueTask DisposeAsync()
    {
        if (Configuration is not null) { await Configuration.DisposeAsync().ConfigureAwait(false); }
        supervisor?.Dispose();
    }
    public override string ToString() => $"Hoard configuration evaluation: {Outcome}";
}

public sealed class HoardValidatedConfiguration : IAsyncDisposable
{
    private readonly HoardValidatedComposition composition;
    private readonly ImmutableDictionary<string, HoardModuleOptions> options;
    private readonly ImmutableArray<IDisposable> resources;
    private bool consumed;
    private bool disposed;
    internal HoardValidatedConfiguration(HoardValidatedComposition composition,
        ImmutableDictionary<string, HoardModuleOptions> options, ImmutableArray<IDisposable> resources)
    { this.composition = composition; this.options = options; this.resources = resources; }
    internal (HoardValidatedComposition Composition, ImmutableDictionary<string, HoardModuleOptions> Options,
        ImmutableArray<IDisposable> Resources) Consume(HoardBuilder builder, CancellationToken token)
    {
        lock (composition.Builder.ConfigurationGate)
        {
            token.ThrowIfCancellationRequested();
            if (consumed || disposed || builder.ConfigurationConsumed || !ReferenceEquals(builder, composition.Builder)
                || composition.Consumed || !builder.Services.SequenceEqual(composition.ServiceSnapshot))
            { throw new HoardLifecycleException([new("StaleConfiguration", "composition", HoardLifecyclePhase.Validating, Guid.NewGuid())]); }
            consumed = true;
            builder.ConfigurationConsumed = true;
            composition.Consumed = true;
            return (composition, options, resources);
        }
    }
    public ValueTask DisposeAsync()
    {
        lock (composition.Builder.ConfigurationGate)
        {
            if (!disposed && !consumed)
            {
                disposed = true;
                foreach (var resource in resources) { resource.Dispose(); }
            }
        }
        return ValueTask.CompletedTask;
    }
    public override string ToString() => "Hoard validated configuration (private)";
}
