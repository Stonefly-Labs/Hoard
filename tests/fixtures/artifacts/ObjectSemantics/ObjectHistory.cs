namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    private readonly Queue<Guid> uploadCandidates = [];
    private readonly Dictionary<Guid, Guid?> indexedTargets = [];
    private readonly Dictionary<Guid, HashSet<Guid>> pointerDependents = [];
    private readonly Queue<string> pointerCandidates = [];

    private void IndexUpload(ObjectOperation upload)
    {
        if (!indexedTargets.TryGetValue(upload.Ticket.Id, out var previous))
        {
            uploadCandidates.Enqueue(upload.Ticket.Id);
            indexedTargets.Add(upload.Ticket.Id, Guid.Empty);
            previous = Guid.Empty;
        }
        if (previous is null) { return; }
        var target = (upload.Selected?.Stamp ?? upload.DeleteTarget)?.Incarnation ?? Guid.Empty;
        if (previous == target) { return; }
        UnlinkUpload(upload.Ticket.Id, previous.Value);
        indexedTargets[upload.Ticket.Id] = target;
        if (target == Guid.Empty) { return; }
        if (!pointerDependents.TryGetValue(target, out var links))
        { pointerDependents.Add(target, links = []); }
        links.Add(upload.Ticket.Id);
    }

    private void UnlinkUpload(Guid id, Guid target)
    {
        if (target == Guid.Empty) { return; }
        var links = pointerDependents[target];
        links.Remove(id);
        if (links.Count == 0) { pointerDependents.Remove(target); }
    }

    private void ReleasePointerDependency(Guid id)
    {
        if (indexedTargets[id] is { } target) { UnlinkUpload(id, target); }
        indexedTargets[id] = null;
    }
}
