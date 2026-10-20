namespace Fixture.Features.One;

internal class Handler
{
    internal static async Task<string> Execute()
    {
        await Task.Yield();
        return Nested.Execute();
    }

    private static class Nested
    {
        internal static string Execute() => Two.Handler.Execute();
    }
}
