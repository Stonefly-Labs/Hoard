namespace Fixture.Features.One;

internal class Handler
{
    internal static string Execute() => Two.Handler.Execute();
}
