namespace Hoard.Artifacts.Tests;

public sealed class ArtifactChildOutputTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Child_capture_accepts_the_exact_bound_and_rejects_overflow_before_return(bool line)
    {
        using var exact = new StringReader(new string('a', 16384) + (line ? "\n" : ""));
        using var overflow = new StringReader(new string('a', 16385) + (line ? "\n" : ""));
        if (line)
        {
            Assert.Equal(new string('a', 16384), await ArtifactChildOutput.ReadLineAsync(exact));
            await Assert.ThrowsAsync<InvalidOperationException>(() => ArtifactChildOutput.ReadLineAsync(overflow));
        }
        else
        {
            Assert.Equal(new string('a', 16384), await ArtifactChildOutput.ReadToEndAsync(exact));
            await Assert.ThrowsAsync<InvalidOperationException>(() => ArtifactChildOutput.ReadToEndAsync(overflow));
        }
    }

    [Fact]
    public async Task Line_capture_preserves_the_next_packet_and_distinguishes_empty_line_from_eof()
    {
        using var input = new StringReader("{}\r\n{}\n\n");
        Assert.Equal("{}", await ArtifactChildOutput.ReadLineAsync(input));
        Assert.Equal("{}", await ArtifactChildOutput.ReadLineAsync(input));
        Assert.Equal("", await ArtifactChildOutput.ReadLineAsync(input));
        Assert.Null(await ArtifactChildOutput.ReadLineAsync(input));
        using var boundary = new StringReader(new string('a', 16384) + "\r\n");
        Assert.Equal(new string('a', 16384), await ArtifactChildOutput.ReadLineAsync(boundary));
    }

    [Fact]
    public async Task Capture_bounds_unterminated_packets_and_preserves_empty_completed_output()
    {
        using var overflow = new StringReader(new string('a', 16385));
        await Assert.ThrowsAsync<InvalidOperationException>(() => ArtifactChildOutput.ReadLineAsync(overflow));
        using var empty = new StringReader("");
        Assert.Equal("", await ArtifactChildOutput.ReadToEndAsync(empty));
    }
}
