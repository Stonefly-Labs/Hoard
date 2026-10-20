namespace Hoard.Hosting.Lifecycle;

internal sealed class ActivationLedger
{
    private readonly object gate = new();
    private readonly HashSet<(string Id, HoardLifecyclePhase Phase)> entered = [];

    internal void Enter(string id, HoardLifecyclePhase phase)
    {
        lock (gate)
        {
            if (!entered.Add((id, phase))) { throw new InvalidOperationException("Lifecycle phase already entered."); }
        }
    }
}
