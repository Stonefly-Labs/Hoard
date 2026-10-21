namespace Hoard.Application.Discovery;

internal sealed record DiscoveryProblem(string Type, string Title, int Status, string Detail, string Code,
    string Phase, Guid CorrelationId, string? ModuleId = null, string? OperationId = null);
