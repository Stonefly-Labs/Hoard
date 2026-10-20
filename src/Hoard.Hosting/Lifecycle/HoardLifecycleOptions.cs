namespace Hoard.Hosting.Lifecycle;

public sealed record HoardLifecycleOptions
{
    public TimeSpan StartupTimeout { get; init; } = TimeSpan.FromSeconds(120);
    public TimeSpan ActivationCallbackTimeout { get; init; } = TimeSpan.FromSeconds(30);
    public TimeSpan ReadinessTimeout { get; init; } = TimeSpan.FromSeconds(5);
    public TimeSpan ShutdownTimeout { get; init; } = TimeSpan.FromSeconds(30);
    public TimeSpan DrainTimeout { get; init; } = TimeSpan.FromSeconds(10);
    public TimeSpan ModuleCleanupTimeout { get; init; } = TimeSpan.FromSeconds(5);

    internal bool IsValid => new[] { StartupTimeout, ActivationCallbackTimeout, ReadinessTimeout,
        ShutdownTimeout, DrainTimeout, ModuleCleanupTimeout }.All(value => value > TimeSpan.Zero);
}
