namespace Fixture.Features.One;

internal class Handler
{
    internal static string Execute() => new FixtureSdk.PrivateModel().ToString()!;
}
