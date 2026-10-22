using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataAtomicityTests
{
    [Fact]
    public async Task MP09_Independent_engine_reads_cannot_see_an_uncommitted_candidate()
    {
        await using var fixture = await OpenAsync();
        await using var barrier = new MetadataTestBarrier();
        var group = new MetadataReadGroup([Registry().Selector, Registry(2).Selector]);
        fixture.Controls.SetObserver("M0", () => new(barrier.HoldAsync()));
        var committing = Commit(fixture, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())).AsTask();
        await barrier.Entered;
        try
        {
            Assert.All(Success(await fixture.ObserveIndependentSnapshotAsync(group)).Items,
                item => Assert.IsType<MetadataReadItem.NotFound>(item));
        }
        finally { barrier.Release(); await committing; fixture.Controls.RemoveObserver("M0"); }
        Assert.All(Success(await fixture.ObserveIndependentSnapshotAsync(group)).Items,
            item => Assert.IsType<MetadataReadItem.Found>(item));
    }

    [Fact]
    public async Task MP09_Each_faulted_candidate_is_invisible_and_success_is_complete()
    {
        await using var fixture = await OpenAsync();
        for (var fault = 1; fault <= 3; fault++)
        {
            var seen = 0;
            fixture.Controls.SetObserver("mutation.applied", () =>
            {
                if (++seen == fault) { throw new InvalidOperationException(MetadataTestData.Canary); }
                return ValueTask.CompletedTask;
            });
            var mutations = Enumerable.Range(1, 3).Select(number =>
                (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray();
            Assert.Equal(MetadataFailureCode.InternalFailure, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture), mutations), new(), default)));
            foreach (var number in Enumerable.Range(1, 3)) { await Missing(fixture, Registry(number).Selector); }
        }
        fixture.Controls.RemoveObserver("mutation.applied");
        await Commit(fixture, Enumerable.Range(1, 3).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        Assert.Equal(3, (await Traverse(fixture, Registries())).Length);
        foreach (var diagnostic in fixture.Controls.Diagnostics) { MetadataTestData.AssertSanitized(diagnostic); }
    }

    [Fact]
    public async Task MP10_Grouped_reads_keep_one_root_while_independent_reads_can_straddle()
    {
        await using var fixture = await OpenAsync();
        await using var barrier = new MetadataTestBarrier();
        var first = Registry();
        var second = Registry(2);
        await Commit(fixture, new MetadataMutation.PutRegistry(first, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(second, new ExpectedRevision.Absent()));
        first = await Read<MetadataRegistry>(fixture, first.Selector);
        second = await Read<MetadataRegistry>(fixture, second.Selector);
        var once = 0;
        fixture.Controls.SetObserver("read.item", () => Interlocked.Increment(ref once) == 1
            ? new ValueTask(barrier.HoldAsync()) : ValueTask.CompletedTask);
        var reading = fixture.Store.ReadAsync(new([first.Selector, second.Selector]), new(), default).AsTask();
        await barrier.Entered;
        var writing = Commit(fixture, new MetadataMutation.PutRegistry(first with { Label = new("new") }, new ExpectedRevision.Match(first.Revision)),
            new MetadataMutation.PutRegistry(second with { Label = new("new") }, new ExpectedRevision.Match(second.Revision))).AsTask();
        barrier.Release();
        var old = Success(await reading);
        await writing;
        Assert.All(old.Items, item => Assert.Equal("synthetic registry", Assert.IsType<MetadataRegistry>(
            Assert.IsType<MetadataReadItem.Found>(item).Record).Label.Value));
        fixture.Controls.RemoveObserver("read.item");
        var snapshot = Success(await fixture.Store.ReadAsync(new([first.Selector, second.Selector]), new(), default));
        Assert.All(snapshot.Items, item => Assert.Equal("new", Assert.IsType<MetadataRegistry>(
            Assert.IsType<MetadataReadItem.Found>(item).Record).Label.Value));
        var before = await Read<MetadataRegistry>(fixture, first.Selector);
        var current = await Read<MetadataRegistry>(fixture, second.Selector);
        await Commit(fixture, new MetadataMutation.PutRegistry(current with { Label = new("later") }, new ExpectedRevision.Match(current.Revision)));
        Assert.NotEqual(before.Label, (await Read<MetadataRegistry>(fixture, second.Selector)).Label);
    }

    [Fact]
    public async Task MP11_Competing_creates_have_one_winner()
    {
        await using var fixture = await OpenAsync();
        var tickets = await Task.WhenAll(Enumerable.Range(0, 8).Select(async _ => await Ticket(fixture)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => fixture.Store.CommitAsync(
            Batch(ticket, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())), new(), default).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(7, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(outcome => outcome.Code == MetadataFailureCode.Conflict));
        Assert.Single(await Traverse(fixture, Registries()));
    }

    [Fact]
    public async Task MP12_Revision_races_and_delete_recreate_are_fenced()
    {
        await using var fixture = await OpenAsync();
        var (registry, _) = await Seed(fixture);
        var tickets = await Task.WhenAll(Enumerable.Range(0, 4).Select(async _ => await Ticket(fixture)));
        var outcomes = await Task.WhenAll(tickets.Select((ticket, number) => fixture.Store.CommitAsync(
            Batch(ticket, new MetadataMutation.PutRegistry(registry with { Label = new(number.ToString(System.Globalization.CultureInfo.InvariantCulture)) },
                new ExpectedRevision.Match(registry.Revision))), new(), default).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(3, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(outcome => outcome.Code == MetadataFailureCode.Conflict));
        var package = Package(registry, "recreated");
        await Commit(fixture, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        package = await Read<MetadataPackage>(fixture, package.Selector);
        await Commit(fixture, new MetadataMutation.DeletePackage(package.Key, package.Revision));
        await Commit(fixture, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()));
        Assert.NotEqual(package.Revision, (await Read<MetadataPackage>(fixture, package.Selector)).Revision);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.DeletePackage(package.Key, package.Revision)), new(), default)));
    }
}
