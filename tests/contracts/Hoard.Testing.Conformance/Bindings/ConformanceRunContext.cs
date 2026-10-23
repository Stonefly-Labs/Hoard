namespace Hoard.Testing.Conformance.Bindings;

public sealed class ConformanceRunContext
{
    public ConformanceRunContext(Guid runId, string caseId, TimeProvider clock,
        IConformanceResourceAllocator resources, IConformanceEvidenceSink evidence)
    {
        if (runId == Guid.Empty) { throw new ArgumentException("BindingInvalid"); }
        ArgumentNullException.ThrowIfNull(clock);
        ArgumentNullException.ThrowIfNull(resources);
        ArgumentNullException.ThrowIfNull(evidence);
        RunId = runId;
        CaseId = ConformanceBindingDeclaration.Id(caseId);
        Clock = clock;
        Resources = resources;
        Evidence = evidence;
    }

    public Guid RunId { get; }
    public string CaseId { get; }
    public TimeProvider Clock { get; }
    public IConformanceResourceAllocator Resources { get; }
    public IConformanceEvidenceSink Evidence { get; }
    public TimeSpan ControlBudget => TimeSpan.FromSeconds(5);
    public TimeSpan BarrierBudget => TimeSpan.FromSeconds(15);
    public TimeSpan CleanupBudget => TimeSpan.FromSeconds(30);
}

public sealed class ConformanceOwnedDirectory
{
    public ConformanceOwnedDirectory(string resourceId, string directoryPath)
    {
        ResourceId = ConformanceBindingDeclaration.Id(resourceId);
        ArgumentException.ThrowIfNullOrEmpty(directoryPath);
        DirectoryPath = directoryPath;
    }

    public string ResourceId { get; }
    public string DirectoryPath { get; }
    public override string ToString() => ResourceId;
}

public interface IConformanceResourceAllocator
{
    ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken cancellationToken);
    ValueTask<ConformanceCleanupObservation> ReleaseAsync(
        ConformanceOwnedDirectory resource, CancellationToken cancellationToken);
}

public interface IConformanceEvidenceSink
{
    ValueTask ObserveAsync(ConformanceFaultObservation observation, CancellationToken cancellationToken);
}
