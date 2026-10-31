using System.Security.Cryptography;

namespace Hoard.Testing.Conformance.Artifacts;

internal sealed class ArtifactHashingSink : Stream
{
    private readonly IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    private long nextPace = 4194304;
    public long BytesWritten { get; private set; }
    public bool Paced { get; private set; }
    public string Digest => Convert.ToHexStringLower(hash.GetCurrentHash());
    public override bool CanRead => false;
    public override bool CanSeek => false;
    public override bool CanWrite => true;
    public override long Length => throw new NotSupportedException();
    public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
    public override async ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (BytesWritten >= nextPace)
        {
            await Task.Delay(TimeSpan.FromMilliseconds(1), cancellationToken);
            nextPace = checked(nextPace + 4194304);
            Paced = true;
        }
        hash.AppendData(buffer.Span);
        BytesWritten = checked(BytesWritten + buffer.Length);
    }
    protected override void Dispose(bool disposing) { if (disposing) { hash.Dispose(); } base.Dispose(disposing); }
    public override void Flush() => throw new NotSupportedException();
    public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
    public override void SetLength(long value) => throw new NotSupportedException();
    public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
}
