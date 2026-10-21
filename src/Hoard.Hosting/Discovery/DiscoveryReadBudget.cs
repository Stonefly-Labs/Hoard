namespace Hoard.Hosting.Discovery;

internal sealed class DiscoveryReadBudget(HoardDiscoveryOptions options, CancellationToken cancellationToken)
{
    private readonly long started = options.TimeProvider.GetTimestamp();
    internal void Check()
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (options.TimeProvider.GetElapsedTime(started) >= options.Deadline)
        { throw new DiscoveryDeadlineException(); }
    }
}

internal sealed class DiscoveryDeadlineException : Exception;
