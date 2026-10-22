namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    private readonly Queue<Guid> ticketCandidates = [];
    private readonly Dictionary<Guid, Guid?> indexedIncarnations = [];
    private readonly Dictionary<Guid, HashSet<Guid>> historyDependents = [];
    private readonly LinkedList<string> decisionCandidates = [];
    private readonly Dictionary<string, LinkedListNode<string>> decisionNodes = new(StringComparer.Ordinal);
    private readonly LinkedList<Guid> reclamationCandidates = [];
    private readonly Dictionary<Guid, LinkedListNode<Guid>> reclamationNodes = [];

    private void IndexTicket(LocalOperation operation)
    {
        if (!indexedIncarnations.TryGetValue(operation.Id, out var prior))
        {
            ticketCandidates.Enqueue(operation.Id);
            indexedIncarnations.Add(operation.Id, Guid.Empty);
            prior = Guid.Empty;
        }
        // Null retains the expired ticket record without retaining its settled dependency.
        if (prior is null) { return; }
        var next = operation.Content?.Incarnation ?? Guid.Empty;
        if (prior == next) { return; }
        UnlinkTicket(operation.Id, prior.Value);
        indexedIncarnations[operation.Id] = next;
        if (next == Guid.Empty) { return; }
        if (!historyDependents.TryGetValue(next, out var dependents))
        { historyDependents.Add(next, dependents = []); }
        dependents.Add(operation.Id);
    }

    private void UnlinkTicket(Guid ticket, Guid incarnation)
    {
        if (incarnation == Guid.Empty) { return; }
        var dependents = historyDependents[incarnation];
        dependents.Remove(ticket);
        if (dependents.Count == 0) { historyDependents.Remove(incarnation); }
    }

    private void ReleaseHistoryDependency(Guid ticket)
    {
        if (indexedIncarnations[ticket] is { } incarnation) { UnlinkTicket(ticket, incarnation); }
        indexedIncarnations[ticket] = null;
    }

    private void IndexDecision(LocalDecision decision)
    {
        if (!decisionNodes.ContainsKey(decision.Content.Digest))
        { decisionNodes.Add(decision.Content.Digest, decisionCandidates.AddLast(decision.Content.Digest)); }
    }

    private void IndexReclamation(LocalDecision decision)
    {
        if (!reclamationNodes.ContainsKey(decision.Content.Incarnation))
        { reclamationNodes.Add(decision.Content.Incarnation, reclamationCandidates.AddLast(decision.Content.Incarnation)); }
    }

    private void ForgetDecision(string digest)
    {
        decisions.Remove(digest);
        decisionCandidates.Remove(decisionNodes[digest]);
        decisionNodes.Remove(digest);
    }

    private void ForgetReclamation(Guid incarnation)
    {
        removedContent.Remove(incarnation);
        reclamationCandidates.Remove(reclamationNodes[incarnation]);
        reclamationNodes.Remove(incarnation);
    }

    private void ClearHistoryIndexes()
    {
        ticketCandidates.Clear();
        indexedIncarnations.Clear();
        historyDependents.Clear();
        decisionCandidates.Clear();
        decisionNodes.Clear();
        reclamationCandidates.Clear();
        reclamationNodes.Clear();
    }
}
