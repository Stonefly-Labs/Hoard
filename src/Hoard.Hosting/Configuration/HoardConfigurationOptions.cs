namespace Hoard.Hosting.Configuration;

public sealed record HoardConfigurationOptions
{
    public double EvaluationTimeoutMilliseconds { get; init; } = 30_000;
    public double OperationTimeoutMilliseconds { get; init; } = 5_000;
    public TimeProvider TimeProvider { get; init; } = TimeProvider.System;
    public int MaximumDocumentBytes { get; init; } = 1024 * 1024;
    public int MaximumDepth { get; init; } = 16;
    public int MaximumAssignments { get; init; } = 4096;
    public int MaximumSelectionIds { get; init; } = 256;
    public int MaximumFieldsPerModule { get; init; } = 256;
    public int MaximumStringBytes { get; init; } = 16 * 1024;
    public int MaximumSecretBytes { get; init; } = 64 * 1024;
    public int MaximumDiagnostics { get; init; } = 100;
    private static bool ValidBudget(double value)
    {
        if (!double.IsFinite(value) || value <= 0) { return false; }
        try { return TimeSpan.FromMilliseconds(value) > TimeSpan.Zero; }
        catch (OverflowException) { return false; }
    }
    internal bool IsValid => ValidBudget(EvaluationTimeoutMilliseconds) && ValidBudget(OperationTimeoutMilliseconds) && TimeProvider is not null
        && MaximumDocumentBytes is > 0 and <= 1024 * 1024 && MaximumDepth is > 0 and <= 16
        && MaximumAssignments is > 0 and <= 4096 && MaximumSelectionIds is > 0 and <= 256
        && MaximumFieldsPerModule is > 0 and <= 256 && MaximumStringBytes is > 0 and <= 16 * 1024
        && MaximumSecretBytes is > 0 and <= 64 * 1024 && MaximumDiagnostics is > 0 and <= 100;
}
