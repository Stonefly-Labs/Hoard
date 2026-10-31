using System.Text.Json;
using Hoard.Conformance.TestLogger;
using Hoard.Testing.Conformance.Diagnostics;
using Microsoft.TestPlatform.VsTestConsole.TranslationLayer;

try
{
    if (args.Length != 5)
    { throw new InvalidDataException("EvidenceSchemaInvalid"); }
    var root = Path.GetFullPath(args[0]);
    var request = RuntimeCaseDiscovery.ReadRequest(root, args[2], args[3]);
    var assembly = Path.Combine(root, request.Assemblies.Single(image => image.Id == "test-assembly").Path);
    var collector = new RuntimeCaseDiscovery(assembly, request.Methods);
    var wrapper = new VsTestConsoleWrapper(Path.GetFullPath(args[1]));
    try
    {
        wrapper.StartSession();
        wrapper.InitializeExtensions([Path.Combine(Path.GetDirectoryName(assembly)!,
            "xunit.runner.visualstudio.testadapter.dll")]);
        wrapper.DiscoverTests([assembly],
            "<RunSettings><RunConfiguration><MaxCpuCount>1</MaxCpuCount>"
            + "<TestSessionTimeout>120000</TestSessionTimeout></RunConfiguration></RunSettings>", collector);
        if (collector.Diagnostic != ConformanceDiagnosticCode.None)
        { throw new InvalidDataException(collector.Diagnostic.ToString()); }
        var bytes = JsonSerializer.SerializeToUtf8Bytes(collector.Cases,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
        if (bytes.Length > 2 * 1024 * 1024) { throw new InvalidDataException("OutputLimitExceeded"); }
        RuntimeCaseDiscovery.ReadRequest(root, args[2], args[3]);
        using (var output = RuntimeCaseDiscovery.CreateOutput(root, args[4]))
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
