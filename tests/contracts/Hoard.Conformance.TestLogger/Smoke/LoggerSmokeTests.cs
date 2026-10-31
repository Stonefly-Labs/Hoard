using System.Runtime.CompilerServices;
using Hoard.Conformance.Tests;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;

namespace Hoard.Testing.Conformance;

public sealed class LoggerSmokeTests(ITestOutputHelper output)
{
    [Fact]
    public async Task OriginOutput()
    {
        var runId = Guid.Parse(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID")
            ?? throw new InvalidOperationException("PrerequisiteMissing"));
        var packageSha = Environment.GetEnvironmentVariable("HOARD_ORIGIN_PACKAGE_SHA256")
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        var declaration = new ConformanceBindingDeclaration("origin-probe", ConformanceCategory.Metadata,
            "Hoard.Testing.Conformance", "0.1.0", packageSha, ["common-logical"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata)
                .OrderBy(fault => fault.ToString(), StringComparer.Ordinal));
        var origin = await BindingContractTests.CaptureMetadataOriginAsync(runId, "runtime", declaration);
        ConformanceSessionOriginOutput.Write(output, origin);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    public void Parameter(int value) => Assert.InRange(value, 1, 2);

    [Fact]
    public void Assertion() => LoggerSmokeAssertion.Check(2);

    [Fact]
    public void Unknown()
    {
        Console.WriteLine("logger-smoke-canary-stdout");
        Console.Error.WriteLine("logger-smoke-canary-stderr");
        throw new InvalidOperationException("logger-smoke-canary-exception");
    }

    [Fact]
    public void PassingOutput() => Console.WriteLine("logger-smoke-canary-passing-stdout");

    [Fact(Skip = "logger-smoke-canary-skip")]
    public void Skipped() => Assert.Fail("logger-smoke-canary-skipped-body");
}

internal static class LoggerSmokeAssertion
{
    [MethodImpl(MethodImplOptions.NoInlining)]
    internal static void Check(int actual) => Assert.Equal(1, actual);
}
