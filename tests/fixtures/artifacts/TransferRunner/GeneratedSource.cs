using System.Security.Cryptography;

namespace Hoard.Fixtures.Artifacts.TransferRunner;

internal sealed class GeneratedSource(long size) : Stream
{
    private readonly byte[] pattern = Enumerable.Range(0, 262144).Select(index => (byte)((index * 31 + 7) % 251)).ToArray();
    private readonly IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    private string? digest;
    private long nextPace = 4194304;
    public long BytesRead { get; private set; }
    public bool Paced { get; private set; }
    public string Digest => digest ?? throw new InvalidOperationException("Artifact source has not reached EOF.");
    public override bool CanRead => true;
    public override bool CanSeek => false;
    public override bool CanWrite => false;
    public override long Length => throw new NotSupportedException();
    public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
    public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (BytesRead == size)
        {
            digest ??= Convert.ToHexStringLower(hash.GetHashAndReset());
            return 0;
        }
        if (BytesRead >= nextPace)
        {
            await Task.Delay(TimeSpan.FromMilliseconds(1), cancellationToken);
            nextPace = checked(nextPace + 4194304);
            Paced = true;
        }
        var offset = (int)(BytesRead % pattern.Length);
        var count = (int)Math.Min(Math.Min(buffer.Length, pattern.Length - offset), size - BytesRead);
        pattern.AsMemory(offset, count).CopyTo(buffer);
        hash.AppendData(buffer.Span[..count]);
        BytesRead = checked(BytesRead + count);
        return count;
    }
    protected override void Dispose(bool disposing) { if (disposing) { hash.Dispose(); } base.Dispose(disposing); }
    public override void Flush() => throw new NotSupportedException();
    public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
    public override void SetLength(long value) => throw new NotSupportedException();
    public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
}
