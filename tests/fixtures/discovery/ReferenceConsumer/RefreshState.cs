namespace Hoard.Discovery.ReferenceConsumer;

public sealed class RefreshState(TimeProvider? timeProvider = null)
{
    private readonly TimeProvider clock = timeProvider ?? TimeProvider.System;
    private long generation;
    private long completedGeneration;
    private long received;
    private string state = "loading";
    public ConsumerObservation? Observation { get; private set; }
    public string State => Observation is not null && (state is "current" or "empty")
        && clock.GetElapsedTime(received) > TimeSpan.FromSeconds(30) ? "stale" : state;
    public bool Current => State is "current" or "empty";

    public long Begin()
    {
        state = Observation is null ? "loading" : "refreshing";
        return checked(++generation);
    }

    public bool Complete(long attempt, int status, ReadOnlyMemory<byte> body)
    {
        if (attempt <= completedGeneration || attempt != generation) { return false; }
        completedGeneration = attempt;
        if (status is 401 or 403)
        { Observation = null; state = "denied"; return false; }
        var result = status == 200 ? DiscoveryJsonReader.Read(body) : new(false, "failed-refresh", null);
        if (!result.Compatible)
        { state = Observation is null ? "error" : "stale"; return false; }
        var next = result.Observation!;
        if (Observation is { } previous && next.LifecycleId == previous.LifecycleId
            && DiscoveryJsonReader.CompareRevision(next.Revision, previous.Revision) < 0)
        { state = "stale"; return false; }
        Observation = next;
        received = clock.GetTimestamp();
        state = next.Modules.IsEmpty ? "empty" : "current";
        return true;
    }
}
