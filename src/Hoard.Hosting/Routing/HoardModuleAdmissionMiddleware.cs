using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;

namespace Hoard.Hosting.Routing;

internal sealed class HoardModuleAdmissionMiddleware(HoardLifecycleCoordinator coordinator) : IStartupFilter
{
    public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
    {
        app.Use(nextRequest => context =>
        {
            var completion = new RequestCompletion(coordinator);
            context.Features.Set(completion);
            // Registered before host middleware so reverse-order completion releases leases last.
            context.Response.OnCompleted(completion.CompleteAsync);
            return nextRequest(context);
        });
        next(app);
    };

    internal static async Task DispatchAsync(HttpContext context, HoardOwnedRoute route, HoardLifecycleCoordinator coordinator)
    {
        var completion = context.Features.Get<RequestCompletion>()
            ?? throw coordinator.Error("MissingMapping", route.ModuleId, HoardLifecyclePhase.Running);
        if (!completion.TryAdmit(route.ModuleId))
        {
            context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
            await context.Response.WriteAsync("Hoard module traffic is not admitted.").ConfigureAwait(false);
            return;
        }
        await route.Handler(context).ConfigureAwait(false);
    }

    private sealed class RequestCompletion(HoardLifecycleCoordinator coordinator)
    {
        private readonly object gate = new();
        private readonly List<IDisposable> activities = [];
        private bool completed;

        internal bool TryAdmit(string owner)
        {
            lock (gate)
            {
                if (completed || coordinator.TryAdmit(owner) is not { } activity) { return false; }
                activities.Add(activity);
                return true;
            }
        }

        internal Task CompleteAsync()
        {
            lock (gate)
            {
                completed = true;
                foreach (var activity in activities) { activity.Dispose(); }
                activities.Clear();
            }
            return Task.CompletedTask;
        }
    }
}
