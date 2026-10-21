namespace Discovery.CrossSlice.Features.One;

internal sealed class Handler
{
    internal int Handle() => new Two.Handler().Handle();
}
