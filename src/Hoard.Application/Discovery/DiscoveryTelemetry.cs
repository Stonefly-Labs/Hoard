using System.Diagnostics.Metrics;

namespace Hoard.Application.Discovery;

internal static class DiscoveryTelemetry
{
    private static readonly Meter Meter = new("Hoard.Discovery");
    private static readonly Counter<long> Reads = Meter.CreateCounter<long>("hoard.discovery.reads");
    internal static void Record(string outcome, string code, string phase, string route) =>
        Reads.Add(1, new("outcome", outcome), new("reason", code), new("phase", phase), new("route", route));
}
