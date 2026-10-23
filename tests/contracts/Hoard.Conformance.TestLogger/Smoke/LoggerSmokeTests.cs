using System.Runtime.CompilerServices;

namespace Hoard.Testing.Conformance;

public sealed class LoggerSmokeTests
{
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
