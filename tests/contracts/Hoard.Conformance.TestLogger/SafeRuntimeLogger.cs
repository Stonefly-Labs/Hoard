using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Microsoft.VisualStudio.TestPlatform.ObjectModel.Client;

namespace Hoard.Conformance.TestLogger;

[FriendlyName("HoardSafe")]
[ExtensionUri("logger://hoard/conformance/runtime/v1")]
public sealed class SafeRuntimeLogger : ITestLoggerWithParameters
{
    private RuntimeResultRecorder? recorder;

    public void Initialize(TestLoggerEvents events, string testRunDirectory) =>
        Emit(ConformanceDiagnosticCode.OwnershipInvalid, 0);

    public void Initialize(TestLoggerEvents events, Dictionary<string, string?> parameters)
    {
        try
        {
            RuntimeSafety.Require(parameters.TryGetValue("Root", out var root)
                && root is not null && parameters.GetValueOrDefault("AttemptId") is not null
                && parameters.GetValueOrDefault("ManifestSha256") is not null
                && parameters.GetValueOrDefault("OwnerSha256") is not null, "OwnershipInvalid");
            recorder = new RuntimeResultRecorder(root, Guid.ParseExact(parameters["AttemptId"]!, "D"),
                parameters["ManifestSha256"]!, parameters["OwnerSha256"]!);
            events.TestResult += (_, args) => recorder.Observe(args.Result);
            events.TestRunMessage += (_, args) => recorder.ObserveMessage(args.Message);
            events.TestRunComplete += (_, args) =>
            {
                recorder.Complete(args.IsAborted || args.IsCanceled || args.Error is not null);
                Emit(recorder.Diagnostic, recorder.ObservedCount);
            };
        }
        catch (Exception error) { Emit(RuntimeResultRecorder.SafeCode(error), 0); }
    }

    private static void Emit(ConformanceDiagnosticCode code, int count) =>
        Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(new { @event = "control", code = code.ToString(), value = count }));
}
