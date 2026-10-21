using System.Buffers;
using System.Text.Json;
using System.Text.Json.Serialization;
using Hoard.Hosting.Discovery;
using Microsoft.AspNetCore.Http;

namespace Hoard.Application.Discovery;

internal static class DiscoveryResponseWriter
{
    internal sealed class Budget(HoardDiscoveryOptions options, CancellationToken token)
    {
        private readonly long started = options.TimeProvider.GetTimestamp();
        internal void Check()
        {
            token.ThrowIfCancellationRequested();
            if (options.TimeProvider.GetElapsedTime(started) >= options.Deadline) { throw new ReadDeadlineException(); }
        }
    }
    private sealed class ReadDeadlineException : Exception;
    private sealed class ResponseLimitException : Exception;
    private sealed class CappedBuffer(int limit, Budget budget) : IBufferWriter<byte>, IDisposable
    {
        private readonly MemoryStream buffer = new();
        private byte[] scratch = [];
        internal long Length => buffer.Length;
        internal byte[] GetBuffer() => buffer.GetBuffer();
        public void Dispose() => buffer.Dispose();
        public Memory<byte> GetMemory(int sizeHint = 0)
        {
            budget.Check();
            // Public tokens are bounded; reject oversized serializer reservations before allocation.
            if (sizeHint > 16384) { throw new ResponseLimitException(); }
            ArgumentOutOfRangeException.ThrowIfNegative(sizeHint);
            if (scratch.Length < Math.Max(4096, sizeHint)) { scratch = new byte[Math.Max(4096, sizeHint)]; }
            return scratch;
        }
        public Span<byte> GetSpan(int sizeHint = 0) => GetMemory(sizeHint).Span;
        public void Advance(int count)
        {
            budget.Check();
            ArgumentOutOfRangeException.ThrowIfNegative(count);
            if (count > scratch.Length) { throw new ArgumentOutOfRangeException(nameof(count)); }
            if (Length > limit - count) { throw new ResponseLimitException(); }
            var required = checked((int)Length + count);
            if (buffer.Capacity < required)
            { buffer.Capacity = Math.Min(limit, Math.Max(required, Math.Max(4096, buffer.Capacity * 2))); }
            buffer.Write(scratch.AsSpan(0, count));
        }
        internal void Write(ReadOnlySpan<byte> bytes)
        {
            while (!bytes.IsEmpty)
            {
                var length = Math.Min(bytes.Length, 4096);
                bytes[..length].CopyTo(GetSpan(length));
                Advance(length);
                bytes = bytes[length..];
            }
        }
    }

    internal static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    { DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull };

    internal static async Task SendAsync(HttpContext context, HoardDiscoveryOptions options, Budget budget,
        Func<object> project, string route, bool description = false)
    {
        try
        {
            budget.Check();
            using var buffer = new CappedBuffer(options.MaximumResponseBytes, budget);
            if (description) { buffer.Write((byte[])project()); }
            else
            {
                using var writer = new Utf8JsonWriter(buffer);
                JsonSerializer.Serialize(writer, project(), Json);
                writer.Flush();
            }
            budget.Check();
            context.Response.OnStarting(() => { context.RequestAborted.ThrowIfCancellationRequested(); return Task.CompletedTask; });
            context.Response.StatusCode = 200;
            context.Response.ContentType = "application/json";
            context.Response.ContentLength = buffer.Length;
            await context.Response.Body.WriteAsync(buffer.GetBuffer().AsMemory(0, checked((int)buffer.Length)),
                context.RequestAborted).ConfigureAwait(false);
            DiscoveryTelemetry.Record("success", "none", description ? "description" : "encoding", route);
        }
        catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
        {
            DiscoveryTelemetry.Record("failure", "cancelled", "encoding", route);
            context.Abort();
        }
        catch (ReadDeadlineException)
        { await ProblemAsync(context, 503, "deadline", "encoding", "Retry a bounded current authorized observation.", route).ConfigureAwait(false); }
        catch (ResponseLimitException)
        { await ProblemAsync(context, 503, "response-limit", "encoding", "Reduce the explicit public catalog to the documented response bounds and restart.", route).ConfigureAwait(false); }
    }

    internal static async Task ProblemAsync(HttpContext context, int status, string code, string phase, string detail, string route)
    {
        DiscoveryTelemetry.Record("failure", code, phase, route);
        if (context.RequestAborted.IsCancellationRequested) { context.Abort(); return; }
        context.Response.StatusCode = status;
        context.Response.ContentLength = null;
        context.Response.ContentType = "application/problem+json";
        await JsonSerializer.SerializeAsync(context.Response.Body,
            new DiscoveryProblem("about:blank", "Discovery unavailable", status, detail, code, phase, Guid.NewGuid()),
            Json, context.RequestAborted).ConfigureAwait(false);
    }
}
