using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactDeletionTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactDeletionAssertions.PendingReclamationAsync(driver.Store, driver.Maintenance, driver.Identity,
            observer => SetObserver(driver, "delete.removed", "pointer.tombstone", observer), default);
        driver.ObserveOriginal(output, nameof(ArtifactDeletionTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
            driver.Store, driver.Maintenance, driver.Identity, default);
        driver.ObserveOriginal(output, nameof(ArtifactDeletionTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Live_reference_or_unavailable_reference_authority_denies_removal(string provider)
    {
        var count = 1L;
        var available = true;
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(available, count, Guid.NewGuid())));
        await ArtifactDeletionAssertions.LiveReferencesAsync(driver.Store,
            value => count = value, value => available = value, default);
        driver.ObserveOriginal(output, nameof(ArtifactDeletionTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactDeletionTests));
    }
}
