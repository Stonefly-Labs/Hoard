namespace Hoard.Abstractions.Storage;

public sealed record ArtifactLimits : ArtifactDiagnostic
{
    public const long MaximumArtifactBytes = 8L * 1024 * 1024 * 1024;
    public const long MaximumStagingBytes = 16L * 1024 * 1024 * 1024;
    public ArtifactLimits(long artifactBytes = MaximumArtifactBytes, long stagingBytes = MaximumStagingBytes,
        int transferSlots = 4, int waitingCalls = 32, int copyBufferBytes = 262144,
        int transferBufferBytes = 2097152, int liveTickets = 100000, int committedIdentities = 100000,
        int decisionBytes = 16384, int pageBytes = 1048576)
    {
        ArtifactValidation.Require(artifactBytes is > 0 and <= MaximumArtifactBytes
            && stagingBytes >= artifactBytes && stagingBytes <= MaximumStagingBytes
            && transferSlots is > 0 and <= 4 && waitingCalls is >= 0 and <= 32
            && copyBufferBytes is > 0 and <= 262144
            && transferBufferBytes >= copyBufferBytes && transferBufferBytes <= 2097152
            && liveTickets is > 0 and <= 100000 && committedIdentities is > 0 and <= 100000
            && decisionBytes is > 0 and <= 16384 && pageBytes is > 0 and <= 1048576);
        _ = checked((long)transferSlots * transferBufferBytes);
        ArtifactBytes = artifactBytes;
        StagingBytes = stagingBytes;
        TransferSlots = transferSlots;
        WaitingCalls = waitingCalls;
        CopyBufferBytes = copyBufferBytes;
        TransferBufferBytes = transferBufferBytes;
        LiveTickets = liveTickets;
        CommittedIdentities = committedIdentities;
        DecisionBytes = decisionBytes;
        PageBytes = pageBytes;
    }
    public long ArtifactBytes { get; }
    public long StagingBytes { get; }
    public int TransferSlots { get; }
    public int WaitingCalls { get; }
    public int CopyBufferBytes { get; }
    public int TransferBufferBytes { get; }
    public int LiveTickets { get; }
    public int CommittedIdentities { get; }
    public int DecisionBytes { get; }
    public int PageBytes { get; }
}

public sealed record ArtifactCallOptions : ArtifactDiagnostic
{
    public ArtifactCallOptions(TimeSpan? deadline = null)
        => Deadline = ArtifactValidation.Duration(deadline ?? TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30));
    public TimeSpan Deadline { get; }
}

public sealed record ArtifactTransferOptions : ArtifactDiagnostic
{
    public ArtifactTransferOptions(TimeSpan? deadline = null, TimeSpan? inactivity = null)
    {
        Deadline = ArtifactValidation.Duration(deadline ?? TimeSpan.FromMinutes(10), TimeSpan.FromMinutes(30));
        Inactivity = ArtifactValidation.Duration(inactivity ?? TimeSpan.FromSeconds(30), TimeSpan.FromMinutes(2));
    }
    public TimeSpan Deadline { get; }
    public TimeSpan Inactivity { get; }
}

public sealed record ArtifactCleanupOptions : ArtifactDiagnostic
{
    public ArtifactCleanupOptions(TimeSpan? deadline = null)
        => Deadline = ArtifactValidation.Duration(deadline ?? TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30));
    public TimeSpan Deadline { get; }
}

public sealed record ArtifactMaintenanceOptions : ArtifactDiagnostic
{
    public ArtifactMaintenanceOptions(TimeSpan? deadline = null)
        => Deadline = ArtifactValidation.Duration(deadline ?? TimeSpan.FromSeconds(30), TimeSpan.FromMinutes(2));
    public TimeSpan Deadline { get; }
}

public sealed record ArtifactOwnershipOptions : ArtifactDiagnostic
{
    public ArtifactOwnershipOptions(TimeSpan? ttl = null, TimeSpan? renewal = null)
    {
        Ttl = ArtifactValidation.Duration(ttl ?? TimeSpan.FromSeconds(30), TimeSpan.FromMinutes(2));
        Renewal = renewal ?? TimeSpan.FromSeconds(10);
        ArtifactValidation.Require(Renewal == TimeSpan.FromSeconds(10) && Ttl > Renewal);
    }
    public TimeSpan Ttl { get; }
    public TimeSpan Renewal { get; }
}
