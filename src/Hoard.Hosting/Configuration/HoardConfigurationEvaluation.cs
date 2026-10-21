using System.Collections.Immutable;

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
    private HoardValidatedConfiguration() { }
    public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    public override string ToString() => "Hoard validated configuration (private)";
}
