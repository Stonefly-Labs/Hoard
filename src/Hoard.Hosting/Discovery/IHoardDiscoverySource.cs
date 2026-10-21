namespace Hoard.Hosting.Discovery;

public interface IHoardDiscoverySource
{
    HoardDiscoveryReadResult Capture(CancellationToken cancellationToken = default);
}
