using Hoard.Hosting.Discovery;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryRouteBindingTests
{
    [Theory]
    [InlineData("GET", "usable")]
    [InlineData("POST", "unavailable")]
    public async Task Only_the_actual_owned_method_satisfies_the_binding(string method, string expected)
    {
        LifecycleFixtures.Reset();
        var invoked = 0;
        LifecycleFixtures.For("protocol").Map = endpoints =>
            endpoints.Map("inspect", "/actual", [method], context =>
            { Interlocked.Increment(ref invoked); return context.Response.WriteAsync("actual"); });
        var (app, lease) = await DiscoveryFixtures.Build();
        await using (lease)
        {
            await app.StartAsync();
            Assert.Equal(expected, DiscoveryFixtures.Capability(lease.Discovery!).Availability);
            Assert.Equal(0, invoked);
            using var client = app.GetTestClient();
            using var request = new HttpRequestMessage(new HttpMethod(method), "/actual");
            using var response = await client.SendAsync(request);
            Assert.True(response.IsSuccessStatusCode);
            Assert.Equal(1, invoked);
        }
    }
}
