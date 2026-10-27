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
        public Task? Work { get; private set; }
        public void Release() => release.TrySetResult();

        public Task RunAsync(CancellationToken cancellationToken) => Work = RunCoreAsync(cancellationToken);

        private async Task RunCoreAsync(CancellationToken cancellationToken)
        {
            entered.TrySetResult();
            try
            {
                if (cooperative) { await release.Task.WaitAsync(cancellationToken); }
                else { await release.Task; }
                if (failAfterRelease)
                {
                    throw new InvalidOperationException(
                        "credential=conformance-secret; https://unsafe.example/token; /private/conformance",
                        new Exception("seeded-secret"));
                }
            }
            finally { settled.TrySetResult(); }
        }
    }
}
