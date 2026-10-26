using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataCorruptionAssertions
{
    public static async Task ScopeOwnershipAsync(
        IMetadataStore store,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        Func<Task> reopenAsync, Func<Task> disposeAsync, bool operation, CancellationToken cancellationToken)
    {
        var registry = Registry();
        var receipt = await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken));
        var foreign = await Ticket(store, cancellationToken);
        MetadataCorruptionRequest request = operation
            ? new MetadataCorruptionRequest.Operation(receipt.Ticket, MetadataOperationCorruption.MissingReceipt, foreign)
            : new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        MetadataCorruptionRequest overlapping = operation
            ? new MetadataCorruptionRequest.Operation(receipt.Ticket, MetadataOperationCorruption.InvalidState, foreign)
            : new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.MalformedEncoding);
        await using var scope = await corruptAsync(request, cancellationToken);
        var damaged = await scope.ObserveAsync(cancellationToken);
        Assert.NotEqual(scope.Original, damaged);
        await Assert.ThrowsAsync<InvalidOperationException>(() => corruptAsync(overlapping, cancellationToken).AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(reopenAsync);
        await Assert.ThrowsAsync<InvalidOperationException>(disposeAsync);
        Assert.Equal(damaged, await scope.ObserveAsync(cancellationToken));
        await Task.WhenAll(scope.DisposeAsync().AsTask(), scope.DisposeAsync().AsTask());
        Assert.Equal(scope.Original, await scope.ObserveAsync(cancellationToken));
        await using var replacement = await corruptAsync(request, cancellationToken);
        await scope.DisposeAsync();
        Assert.Equal(damaged, await replacement.ObserveAsync(cancellationToken));
        await Assert.ThrowsAsync<InvalidOperationException>(disposeAsync);
        await replacement.DisposeAsync();
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken)));
        Assert.Equal<byte>(MetadataEncoding.Encode(receipt), MetadataEncoding.Encode(
            Assert.IsType<MetadataResolution.Committed>(
                Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken))).Receipt));
    }

    public static async Task CaptureConflictAsync(
        IMetadataStore store, MetadataObservationControl observe,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        bool operation, CancellationToken cancellationToken)
    {
        var registry = Registry();
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        registry = await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        var ticket = await Ticket(store, cancellationToken);
        var foreign = await Ticket(store, cancellationToken);
        var captured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = await observe(MetadataObservationPoint.CorruptionCaptured, () =>
        {
            captured.TrySetResult();
            return new(release.Task);
        }, cancellationToken);
        MetadataCorruptionRequest request = operation
            ? new MetadataCorruptionRequest.Operation(ticket, MetadataOperationCorruption.InvalidState, foreign)
            : new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        var corrupting = corruptAsync(request, cancellationToken).AsTask();
        var updated = registry with { Label = new("intervening committed registry"), Revision = new(Guid.NewGuid()) };
        Exception? error = null;
        try
        {
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken);
            Success(await store.CommitAsync(Batch(ticket,
                new MetadataMutation.PutRegistry(updated, new ExpectedRevision.Match(registry.Revision))), new(), cancellationToken));
            updated = await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        }
        finally
        {
            release.TrySetResult();
            error = await Record.ExceptionAsync(async () => { await using var scope = await corrupting; });
        }
        Assert.Equal<byte>(MetadataEncoding.Encode(updated),
            MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken)));
        Assert.IsType<MetadataResolution.Committed>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal("FaultControl.Conflict", Assert.IsType<InvalidOperationException>(error).Message);
    }

    public static async Task ClosureAdmissionAsync(
        IMetadataStore store, MetadataObservationControl observe,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        Func<Task> closeAsync, CancellationToken cancellationToken)
    {
        var registry = Registry();
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        registry = await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = await observe(MetadataObservationPoint.MutationApplied, () =>
        {
            entered.TrySetResult();
            return new(release.Task);
        }, cancellationToken);
        var updated = registry with { Label = new("held registry"), Revision = new(Guid.NewGuid()) };
        var committing = store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(updated, new ExpectedRevision.Match(registry.Revision))), new(), cancellationToken).AsTask();
        Task? closing = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken);
            closing = closeAsync();
            await Assert.ThrowsAsync<InvalidOperationException>(() => corruptAsync(
                new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel),
                cancellationToken).AsTask().WaitAsync(TimeSpan.FromSeconds(1), cancellationToken));
        }
        finally
        {
            release.TrySetResult();
            await committing;
            if (closing is not null) { await closing; }
        }
    }

    public static async Task CancelledApplicationAsync(
        IMetadataStore store, MetadataObservationControl observe,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        bool operation, CancellationToken cancellationToken)
    {
        var registry = Registry();
        var receipt = await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken));
        var foreign = await Ticket(store, cancellationToken);
        using var cancelled = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        var calls = 0;
        await using var observation = await observe(MetadataObservationPoint.PayloadChanged, () =>
        {
            if (Interlocked.Increment(ref calls) == 1) { cancelled.Cancel(); }
            return ValueTask.CompletedTask;
        }, cancellationToken);
        MetadataCorruptionRequest request = operation
            ? new MetadataCorruptionRequest.Operation(receipt.Ticket, MetadataOperationCorruption.MissingReceipt, foreign)
            : new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => corruptAsync(request, cancelled.Token).AsTask());
        Assert.Equal(2, calls);
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken)));
        Assert.IsType<MetadataResolution.Committed>(Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)));
        await using var replacement = await corruptAsync(request, cancellationToken);
    }

    public static async Task FailedRestorationAsync(
        IMetadataStore store, MetadataObservationControl observe,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        Func<CancellationToken, ValueTask> restoreAsync, Func<Task> disposeAsync,
        bool operation, CancellationToken cancellationToken)
    {
        var registry = Registry();
        var receipt = await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken));
        var foreign = await Ticket(store, cancellationToken);
        var calls = 0;
        await using var observation = await observe(MetadataObservationPoint.PayloadChanged, () =>
        {
            if (Interlocked.Increment(ref calls) <= 2)
            { throw new InvalidOperationException("Synthetic payload observation failure."); }
            return ValueTask.CompletedTask;
        }, cancellationToken);
        MetadataCorruptionRequest request = operation
            ? new MetadataCorruptionRequest.Operation(receipt.Ticket, MetadataOperationCorruption.MissingReceipt, foreign)
            : new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        await Assert.ThrowsAsync<InvalidOperationException>(() => corruptAsync(request, cancellationToken).AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(disposeAsync);
        await restoreAsync(cancellationToken);
        Assert.Equal(3, calls);
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(store, registry.Selector, cancellationToken)));
        Assert.IsType<MetadataResolution.Committed>(Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)));
    }

    public static async Task AbsenceAndCorruptGroupsAsync(
        IMetadataStore store,
        Func<MetadataSelector, CancellationToken, ValueTask<MetadataResult<MetadataId>>> corruptRecordAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptRecordAsync);
        var (registry, package) = await Seed(store, cancellationToken);
        var request = new MetadataReadGroup([package.Selector, Registry(99).Selector, registry.Selector]);
        var before = Success(await store.ReadAsync(request, new(), cancellationToken));
        Assert.Equal(3, before.Items.Length);
        Assert.IsType<MetadataReadItem.NotFound>(before.Items[1]);
        Success(await corruptRecordAsync(registry.Selector, cancellationToken));
        CorruptFailure(await store.ReadAsync(request, new(), cancellationToken), MetadataPhase.Read);
    }

    public static async Task PageRecordsAsync(
        IMetadataStore store,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        Func<MetadataSelector, CancellationToken, ValueTask<MetadataResult<MetadataId>>> corruptRecordAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        ArgumentNullException.ThrowIfNull(corruptRecordAsync);
        var healthy = Registry();
        var damaged = Registry(2) with { Label = new(MetadataReconciliationAssertions.CorruptionCanary) };
        await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(healthy, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(damaged, new ExpectedRevision.Absent()));
        var query = Registries();
        var baseline = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal(2, baseline.Records.Length);
        foreach (var invalid in new[] { query with { PageSize = 101 }, query with
        {
            Continuation = new MetadataOption<MetadataContinuation>.Some(new(MetadataReconciliationAssertions.CorruptionCanary))
        } })
        {
            var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                await store.ReadPageAsync(invalid, new(), cancellationToken));
            Assert.Equal(MetadataFailureCode.InvalidInput, failure.Code);
            Assert.Equal(MetadataRetryDisposition.CorrectInput, failure.Retry);
            Assert.Equal(MetadataPhase.Page, failure.Phase);
            Assert.DoesNotContain(MetadataReconciliationAssertions.CorruptionCanary, failure.ToString());
        }
        foreach (var corruption in new[] { MetadataRecordCorruption.NullLabel, MetadataRecordCorruption.OversizedLabel,
            MetadataRecordCorruption.NullRevision, MetadataRecordCorruption.MalformedEncoding, MetadataRecordCorruption.MismatchedKey })
        {
            await using (var scope = await corruptAsync(
                new MetadataCorruptionRequest.Record(damaged.Selector, corruption), cancellationToken))
            {
                var fingerprint = await scope.ObserveAsync(cancellationToken);
                Assert.NotEqual(scope.Original, fingerprint);
                CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
                CorruptFailure(await store.ReadAsync(new([healthy.Selector, damaged.Selector]), new(), cancellationToken),
                    MetadataPhase.Read);
                Assert.Equal(fingerprint, await scope.ObserveAsync(cancellationToken));
                await Read<MetadataRegistry>(store, healthy.Selector, cancellationToken);
            }
            var restored = Success(await store.ReadPageAsync(query, new(), cancellationToken));
            Assert.Equal<byte>(MetadataEncoding.Encode(baseline), MetadataEncoding.Encode(restored));
            Assert.IsType<MetadataOption<MetadataContinuation>.None>(restored.Continuation);
            await Read<MetadataRegistry>(store, damaged.Selector, cancellationToken);
        }
        Success(await corruptRecordAsync(damaged.Selector, cancellationToken));
        CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
    }

    public static async Task QueryDimensionsAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        MetadataRecordCorruption corruption, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        if (corruption is not (MetadataRecordCorruption.CacheAuthorization or MetadataRecordCorruption.AggregateAuthorization
            or MetadataRecordCorruption.AggregateStart or MetadataRecordCorruption.AggregateEnd or MetadataRecordCorruption.LeaseResource))
        { throw new ArgumentException("BindingInvalid", nameof(corruption)); }
        Evidence.ConformanceMetadataArgumentOutput.Record(store, "query-corruption", corruption.ToString());
        var (registry, package) = await Seed(store, cancellationToken);
        var first = Entry(package, target: "/a");
        var damaged = Entry(package, target: "/b");
        var aggregate = Aggregate(registry);
        await Commit(store, cancellationToken, Publish(authority, first), Publish(authority, damaged),
            Publish(authority, Entry(package, partition: "other", target: "/a0")),
            Publish(authority, Entry(package, partition: "other", target: "/a1")),
            Publish(authority, Entry(package, partition: "other", target: "/a2")),
            new MetadataMutation.AddAggregateContribution(aggregate, Delta()),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry, "other"), Delta()),
            new MetadataMutation.AddAggregateContribution(aggregate with { Start = new(1) }, Delta()),
            new MetadataMutation.AcquireLease(new("maintenance-a"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("maintenance-b"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("other-a"), Id(3), 300));
        MetadataPageQuery query = corruption switch
        {
            MetadataRecordCorruption.CacheAuthorization => new MetadataPageQuery.CacheEntries(
                registry.Id, new("anonymous"), new MetadataOption<MetadataPackageKey>.Some(package.Key))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            MetadataRecordCorruption.LeaseResource => new MetadataPageQuery.Leases(new("maintenance-"))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            _ => new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), aggregate.Start, aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() }
        };
        MetadataSelector selector = corruption switch
        {
            MetadataRecordCorruption.CacheAuthorization => damaged.Selector,
            MetadataRecordCorruption.LeaseResource => new MetadataSelector.Lease(new("maintenance-b")),
            _ => new MetadataSelector.Aggregate(aggregate)
        };
        MetadataPageQuery[] emptyQueries = [
            new MetadataPageQuery.CacheEntries(registry.Id, new("foreign"), None<MetadataPackageKey>())
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("foreign"), aggregate.Start, aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), new(2), aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Leases(new("foreign-"))
            { PageSize = 100, Continuation = None<MetadataContinuation>() }];
        var baseline = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal(corruption is MetadataRecordCorruption.CacheAuthorization or MetadataRecordCorruption.LeaseResource
            ? 2 : 1, baseline.Records.Length);
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(store, empty, cancellationToken)); }
        await using (var scope = await corruptAsync(new MetadataCorruptionRequest.Record(selector, corruption), cancellationToken))
        {
            var fingerprint = await scope.ObserveAsync(cancellationToken);
            Assert.NotEqual(scope.Original, fingerprint);
            CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
            CorruptFailure(await store.ReadAsync(new([registry.Selector, selector]), new(), cancellationToken), MetadataPhase.Read);
            Assert.Equal(fingerprint, await scope.ObserveAsync(cancellationToken));
        }
        var restored = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal<byte>(MetadataEncoding.Encode(baseline), MetadataEncoding.Encode(restored));
        Assert.Equal(baseline.Records.Select(record => record.Selector),
            (await Traverse(store, query with { PageSize = 1 }, cancellationToken)).Select(record => record.Selector));
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(store, empty, cancellationToken)); }
    }
}
