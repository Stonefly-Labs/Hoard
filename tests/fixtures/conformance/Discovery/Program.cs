using System.Text.Json;
using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.TestPlatform.VsTestConsole.TranslationLayer;

try
{
    if (args.Length != 4 || new FileInfo(args[2]).Length is <= 0 or > 1024 * 1024)
    { throw new InvalidDataException("EvidenceSchemaInvalid"); }
    var methods = JsonSerializer.Deserialize<string[]>(File.ReadAllBytes(args[2]))
        ?? throw new InvalidDataException("EvidenceSchemaInvalid");
    var collector = new RuntimeCaseDiscovery(args[1], methods);
    var wrapper = new VsTestConsoleWrapper(Path.GetFullPath(args[0]));
    try
    {
        wrapper.StartSession();
        wrapper.InitializeExtensions([Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[1]))!,
            "xunit.runner.visualstudio.testadapter.dll")]);
        wrapper.DiscoverTests([Path.GetFullPath(args[1])],
            "<RunSettings><RunConfiguration><MaxCpuCount>1</MaxCpuCount>"
            + "<TestSessionTimeout>120000</TestSessionTimeout></RunConfiguration></RunSettings>", collector);
        if (collector.Diagnostic != ConformanceDiagnosticCode.None)
        { throw new InvalidDataException(collector.Diagnostic.ToString()); }
        var bytes = JsonSerializer.SerializeToUtf8Bytes(collector.Cases,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
        if (bytes.Length > 2 * 1024 * 1024) { throw new InvalidDataException("OutputLimitExceeded"); }
        using (var output = new FileStream(args[3], FileMode.CreateNew, FileAccess.Write, FileShare.None))
        { output.Write(bytes); }
        Console.WriteLine(JsonSerializer.Serialize(new { @event = "control", code = "None", value = collector.Cases.Count }));
    }
    finally { wrapper.EndSession(); }
    return 0;
}
catch (Exception error)
{
    var code = error is InvalidDataException
        && Enum.TryParse<ConformanceDiagnosticCode>(error.Message, out var diagnostic)
        && Enum.IsDefined(diagnostic) && diagnostic != ConformanceDiagnosticCode.None
        ? diagnostic : ConformanceDiagnosticCode.UnknownDiagnostic;
    Console.WriteLine(JsonSerializer.Serialize(new { qualification = false, diagnosticCode = code.ToString() }));
    return 2;
}
