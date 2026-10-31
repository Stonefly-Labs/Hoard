using System.Text.Json;

namespace Hoard.Testing.Conformance.Diagnostics;

public enum ConformanceDiagnosticCode
{
    None, AssertionFailed, EvidenceSchemaInvalid, EvidenceIncomplete, InputChanged,
    WitnessMissing, ProofMismatch, BindingInvalid, UnsupportedProfile,
    PrerequisiteMissing, InsufficientCapacity, DeadlineExceeded, OutputLimitExceeded,
    UnknownDiagnostic, CleanupIncomplete, OwnershipInvalid, CommandFailed
}

public static class ConformanceDiagnostic
{
    public static async ValueTask WriteAsync(Stream output, ConformanceDiagnosticCode code, long value,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(output);
        if (!Enum.IsDefined(code) || value < 0) { throw new ArgumentException("EvidenceSchemaInvalid"); }
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new { @event = "control", code = code.ToString(), value });
        await output.WriteAsync(bytes, cancellationToken);
        await output.WriteAsync("\n"u8.ToArray(), cancellationToken);
    }
}
