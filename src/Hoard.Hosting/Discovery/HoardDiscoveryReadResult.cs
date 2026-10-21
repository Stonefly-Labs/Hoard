namespace Hoard.Hosting.Discovery;

public sealed class HoardDiscoveryReadResult
{
    internal HoardDiscoveryReadResult(HoardDiscoveryObservation observation) => Observation = observation;
    internal HoardDiscoveryReadResult(string code) => Failure = new(code, correlationId: Guid.NewGuid());
    public bool Success => Observation is not null;
    public HoardDiscoveryObservation? Observation { get; }
    public DiscoveryReason? Failure { get; }
}
