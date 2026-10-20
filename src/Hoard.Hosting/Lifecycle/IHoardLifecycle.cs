namespace Hoard.Hosting.Lifecycle;

public interface IHoardLifecycle
{
    HoardLifecycleSnapshot Snapshot { get; }
    Task<HoardStartResult> StartAsync(CancellationToken cancellationToken = default);
    Task<HoardLifecycleSnapshot> AssessReadinessAsync(CancellationToken cancellationToken = default);
    Task<HoardStopResult> StopAsync(CancellationToken cancellationToken = default);
}
