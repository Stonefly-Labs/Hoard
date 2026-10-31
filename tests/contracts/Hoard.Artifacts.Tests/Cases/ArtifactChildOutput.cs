using System.Text;

namespace Hoard.Artifacts.Tests;

internal static class ArtifactChildOutput
{
    public static Task<string?> ReadLineAsync(TextReader reader) => ReadAsync(reader, line: true);

    public static async Task<string> ReadToEndAsync(TextReader reader)
        => await ReadAsync(reader, line: false)
            ?? throw new InvalidOperationException("Artifact child capture did not complete.");

    private static async Task<string?> ReadAsync(TextReader reader, bool line)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        var text = new StringBuilder();
        var buffer = new char[1];
        while (await reader.ReadAsync(buffer.AsMemory(), deadline.Token) != 0)
        {
            if (line && buffer[0] == '\n') { return Finish(); }
            if (text.Length >= 16385)
            { throw new InvalidOperationException("Artifact child output exceeded its bound."); }
            text.Append(buffer[0]);
            if (text.Length > 16384 && (!line || buffer[0] != '\r'))
            { throw new InvalidOperationException("Artifact child output exceeded its bound."); }
        }
        return line && text.Length == 0 ? null : Finish();

        string Finish()
        {
            if (line && text.Length > 0 && text[^1] == '\r') { text.Length--; }
            return text.ToString();
        }
    }
}
