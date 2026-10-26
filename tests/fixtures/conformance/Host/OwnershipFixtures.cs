namespace Hoard.Fixtures.Conformance.Host;

public static class OwnershipFixtures
{
    public sealed class ControlledCallback(bool cooperative, bool failAfterRelease = false)
    {
        private readonly TaskCompletionSource entered = CompositionFixtures.Barrier();
        private readonly TaskCompletionSource release = CompositionFixtures.Barrier();
        private readonly TaskCompletionSource settled = CompositionFixtures.Barrier();

        public Task Entered => entered.Task;
        public Task Settled => settled.Task;
        public void Release() => release.TrySetResult();

        public async Task RunAsync(CancellationToken cancellationToken)
        {
            entered.TrySetResult();
            try
            {
                if (cooperative) { await release.Task.WaitAsync(cancellationToken); }
                else { await release.Task; }
                if (failAfterRelease)
                {
                    throw new InvalidOperationException(
                        "credential=conformance-secret; https://unsafe.example/token; /private/conformance");
                }
            }
            finally { settled.TrySetResult(); }
        }
    }
}
