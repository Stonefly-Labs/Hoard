using System.Collections.Immutable;

namespace Hoard.Hosting.Configuration.Conversion;

public enum HoardConfigurationChangeKind { Added, Removed, Changed, ReferenceChanged, SelectionChanged, VersionChanged }
public sealed record HoardConfigurationChange(string Setting, HoardConfigurationChangeKind Kind);
public enum HoardConfigurationApplyOutcome { Published, Rejected, Cancelled, TimedOut, PublicationPending }
public enum HoardConfigurationPublicationStatus { NotPublished, Pending, Published }

public sealed class HoardConfigurationPublication
{
    private int status;
    public HoardConfigurationPublicationStatus Status => (HoardConfigurationPublicationStatus)Volatile.Read(ref status);
    internal void Begin() => Volatile.Write(ref status, (int)HoardConfigurationPublicationStatus.Pending);
    internal void Commit() => Volatile.Write(ref status, (int)HoardConfigurationPublicationStatus.Published);
    internal void Finish() => Interlocked.CompareExchange(ref status,
        (int)HoardConfigurationPublicationStatus.NotPublished, (int)HoardConfigurationPublicationStatus.Pending);
}

public sealed class HoardConfigurationConversionPreview : IAsyncDisposable
{
    private readonly ConfigurationSupervisor supervisor;
    internal HoardConfigurationConversionPreview(ConfigurationSupervisor supervisor,
        HoardConfigurationConversionSession? session, ImmutableArray<HoardConfigurationChange> changes)
    {
        this.supervisor = supervisor; Session = session; Changes = changes;
        Outcome = supervisor.Outcome; Report = ConversionReports.Create(supervisor);
    }
    public HoardConfigurationOutcome Outcome { get; }
    public HoardConfigurationReport Report { get; }
    public HoardConfigurationConversionSession? Session { get; }
    public ImmutableArray<HoardConfigurationChange> Changes { get; }
    public HoardConfigurationSupervision Supervision => supervisor.Snapshot;
    public async ValueTask DisposeAsync()
    {
        if (Session is not null) { await Session.DisposeAsync().ConfigureAwait(false); }
        supervisor.Dispose();
    }
    public override string ToString() => $"Configuration conversion preview: {Outcome}";
}

public sealed class HoardConfigurationConversionApplyResult : IAsyncDisposable
{
    private readonly ConfigurationSupervisor supervisor;
    internal HoardConfigurationConversionApplyResult(HoardConfigurationApplyOutcome outcome,
        ConfigurationSupervisor supervisor, HoardConfigurationPublication publication)
    { Outcome = outcome; this.supervisor = supervisor; Report = ConversionReports.Create(supervisor); Publication = publication; }
    public HoardConfigurationApplyOutcome Outcome { get; }
    public HoardConfigurationReport Report { get; }
    public HoardConfigurationPublication Publication { get; }
    public HoardConfigurationSupervision Supervision => supervisor.Snapshot;
    public ValueTask DisposeAsync() { supervisor.Dispose(); return ValueTask.CompletedTask; }
    public override string ToString() => $"Configuration conversion apply: {Outcome}";
}

internal static class ConversionReports
{
    internal static HoardConfigurationReport Create(ConfigurationSupervisor supervisor) =>
        new(supervisor.Correlation, supervisor.Snapshot.Diagnostics, supervisor.Snapshot.OmittedCount, supervisor.Provenance);
}
