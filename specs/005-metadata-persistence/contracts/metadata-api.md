# F-05 Provider-Neutral Metadata API

**Status**: Implemented opt-in contracts; fixtures are not production providers.
Normative values are in the [model](../data-model.md); proofs are in
[acceptance](acceptance.md). Namespace: `Hoard.Abstractions.Metadata`.

## Ownership and Compatibility

Existing `IMetadataProvider`, other family markers, descriptors, registration
and lifecycle/configuration signatures remain byte/source compatible.
Operational providers additionally implement the following separate interfaces.
Abstractions remains BCL-only. No public signature exposes a connection,
transaction, `DbContext`, SQL, `IQueryable`, arbitrary predicate, vendor exception,
service provider, stream of unbounded records or raw `object` payload.

Signature inventory (types describe the closed records in this contract/model;
these declarations are not implementation bodies):

```csharp
public interface IMetadataStore : IAsyncDisposable
{
    ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
        MetadataCallOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
        MetadataReadGroup request, MetadataCallOptions options,
        CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
        MetadataPageQuery request, MetadataCallOptions options,
        CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
        MetadataMutationBatch request, MetadataCallOptions options,
        CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
        MetadataOperationTicket ticket, MetadataCallOptions options,
        CancellationToken cancellationToken);
}

public interface IMetadataSchemaAdministration
{
    ValueTask<MetadataResult<MetadataSchemaInspection>> InspectAsync(
        MetadataAdministrationOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareAsync(
        MetadataSchemaRequest request, MetadataAdministrationOptions options,
        CancellationToken cancellationToken);
}

public interface IMetadataPublicationAuthority
{
    ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
        MetadataArtifactEvidence evidence, MetadataCallOptions options,
        CancellationToken cancellationToken);
}

public interface IMetadataPublicationGuard : IAsyncDisposable
{
    MetadataCommittedArtifact Artifact { get; }
}
```

`MetadataResult<T>` is a closed success/failure sum (immutable sealed records,
with an inaccessible base constructor). Failure variants cannot carry a
success-shaped default `T`. Exact selector absence is `MetadataReadItem.NotFound`,
not a failed whole read. Optional values use explicit choices. Public diagnostic
formatting excludes identities, record content, ticket/evidence values, URIs,
secret references and exception objects. A receipt contains ticket ID, commit
ID and per-target new revisions/reference observations, never record payloads.

`MetadataResolution` is `Committed(receipt)` or `NotCommitted(abandonedTicket)`;
unresolved lookup uses the `Uncertain` failure. Ticket, cursor and evidence
debug/`ToString` views are redacted. They are trusted in-process handles, not
credentials or HTTP tokens. Do not expose this contract directly as a management
API or use its scope fields instead of authorization.

## Reads and Mutations

Typed selectors identify registry, package, policy, cache entry, artifact state,
lease or aggregate by exact key. All selectors in a read observe one committed
state, including reference counts. At most 64 selectors; one missing item
does not hide another item or turn an outage into a miss.
Artifact reads return digest, length, live count and reference revision, not an
unbounded list of all reference edges; retrieve scoped entries through pages.

`MetadataPageQuery` is a closed hierarchy with the seven query kinds, key order
and continuation rules in the model. No client-controlled SQL/projection/
predicate is accepted. Return immutable typed record collections, last-key
continuation or explicit end, not a lazy database iterator.

`MetadataMutation` is a closed hierarchy with only these operations:

| Mutation | Preconditions / effect |
| --- | --- |
| `PutRegistry`, `PutPackage`, `PutPolicy` | `Absent` or matching revision; validate complete final relationships |
| `DeleteRegistry`, `DeletePackage`, `DeletePolicy` | Match existing revision; no remaining dependents, no implicit cascade |
| `PublishCacheEntry` | Absent/matching revision, accepted artifact guard, matching registry/package/scope; replace entry and edges atomically |
| `DeleteCacheEntry` | Match revision; remove edge and advance artifact reference revision atomically |
| `AddAggregateContribution` | Scoped nonnegative deltas, checked addition; ticket deduplication; not blind replacement of counters |
| `DeleteAggregate` | Match revision; explicit bounded administrative removal |
| `AcquireLease` | Resource not owned at effectiveNow; assign next generation, owner and expiry |
| `RenewLease`, `ReleaseLease` | Match owner/generation/revision and unexpired ownership; tombstone on release |
| `ConfirmUnreferenced` | Match current artifact reference revision and zero live edges; metadata-only receipt |

Batch targets are unique. A whole-batch optional `MetadataLeaseGuard` asserts
resource, owner and generation; it is not a mutation of that same lease in that
batch. Check the guard and expected revisions immediately before commit under
writer exclusion. A group is evaluated as a final graph, not sequential
externally visible writes. Aggregate contributions need no prior revision:
concurrent contributions each add exactly once using distinct reserved tickets.
Delete/recreate and reuse of a stale revision cannot bypass the match rule.

Disabled registries remain readable but `PublishCacheEntry` to them is rejected.
Changing enablement or policy does not silently evict entries; later cache policy
decides their usability. Existing entries retain identity and artifact edges.
Persistence never computes canonicalization, freshness, permissions or byte
integrity; it only validates the supplied structure and transactional invariants.

## Publication Authority Boundary

The host constructs/injects a shared authority into a selected operational
provider; individual mutation callers cannot substitute one. Each publication
supplies an opaque bounded evidence handle, digest and length. The provider
acquires one guard per distinct artifact before opening its transaction, verifies
the returned digest/length exactly, and holds all guards until that transaction
has definitely committed or rolled back. The authority must own the appropriate
cross-store publication/deletion protection; persistence cannot implement it
as a caller assertion or infer it from a declared capability.

An identical committed retry is recognized from its ticket/fingerprint before
needing fresh artifact guards. Initial retries with renewed evidence use the
same logical digest/length fingerprint. A failed acquisition yields an explicit
invalid/unavailable result with no metadata changes. Never call external authority
code while holding a database transaction or internal state lock.

F-05 tests this seam with a host-side controlled authority and tracked guards;
it does not implement the shared cache engine, byte-store verification or F-06.
Guard disposal is owned asynchronous cleanup. If a native commit outlives
caller cancellation, the worker retains the guards until it settles; do not
release cross-store protection merely because caller waiting ended.

## Finite Budgets and Cancellation

`MetadataCallOptions` specifies a positive overall timeout, default five seconds,
maximum 30 seconds; all clocks use monotonic elapsed time for budgets. Invalid
timeouts return `InvalidInput` before allocating a worker or doing I/O.
Request/result limits, queue capacity and ledger limits are common mandatory
maxima; providers cannot advertise larger semantics through silent truncation.

Queue waiting, validation, guard acquisition, contention, I/O and result
construction consume the same budget. At most 32 waiting operations per store;
full admission yields `Capacity`. SQLite uses one owned worker and immediate
busy detection, retrying only lock acquisition in at most 50 ms cooperative
intervals within the original deadline. No retry of a commit with uncertain
outcome. Memory uses the same budget/result semantics without simulating SQLite.

Cancellation before commit decision rolls back and returns definite
`CancelledBeforeCommit` only when rollback/non-entry is known. After an
unobserved commit attempt, return `Uncertain(ticket)` with reconcile guidance,
even if the initiating token is cancelled. Reads/reservation waiting can end
without claiming cancellation of a native call. An uncertain reservation
cannot have changed user records, and an unidentified reserved ticket may expire.

Native/filesystem calls are not hard-preemptible. At the deadline, caller
waiting ends with `DeadlineExceeded` for a known non-commit, or `Uncertain`
where outcome is unknown. The owned worker may settle later; no new work is
admitted while a timed-out native call is unresolved. Shutdown stops admission,
cancels queued work, waits within its finite cleanup budget, and retains
resource ownership if work remains. It must never dispose a connection/guard
under live work or silently report successful cleanup. Existing F-02 host-side
ownership rules apply; a stuck device blocks readiness and clean shutdown,
not the caller result forever.

## Failure Classification

| Result / fixed reason | Meaning | Safe action |
| --- | --- | --- |
| `InvalidInput` | Bounds, shape, relationship, evidence or query mismatch | Correct input; no partial mutation |
| `NotFound` | Exact selector absent in a successful committed snapshot | Caller handles absence; not retry guidance for outage |
| `Conflict` | Duplicate identity, stale revision, fingerprint or lease ownership | Re-read/recompute; do not overwrite or blindly change ticket |
| `CancelledBeforeCommit` | Known no commit for this attempt | Identical request may retry same live ticket |
| `DeadlineExceeded` | Known non-commit or read budget exhausted | Bounded caller-selected retry; same ticket for mutation |
| `Unavailable` | Store access/lock service cannot be established before mutation | Retry only if explicitly marked definite non-commit; otherwise uncertain |
| `Capacity` | Queue, receipt ledger, storage or counter capacity exhausted | Resolve pressure, no provider fallback |
| `CorruptState` | Invalid stored record/integrity failure | Block normal use, operator recovery; never return a miss |
| `IncompatibleSchema` | Empty/not admitted/old/new/unsupported schema for operations | Inspect/authorized prepare or compatible application; never reset |
| `Uncertain` | Commit/abandonment outcome cannot be established | Reconcile exact ticket; never blindly replay under a new ticket |
| `ReconciliationExpired` | Expired, unknown, foreign-epoch or restored-away ticket | Stop automated replay; operator-level reconciliation |
| `Disposed` | Admission closed permanently for this instance | Use only a deliberately initialized new instance |

Result variants include fixed operation phase, reason, retry disposition
(`CorrectInput`, `RetrySameTicket`, `Reconcile`, `OperatorRecovery`, `None`)
and correlation ID. Translate known provider failures at the owning boundary;
unexpected failures surface as sanitized internal failure with explicit
operator-recovery guidance and a safe structured event, never empty success.
Do not attach raw exceptions or silently catch-and-continue. Cancellation and
contention faults must not erase a previously committed receipt.

## Schema and Host Wiring

`InspectAsync` returns `Empty`, `Compatible`, `UpgradeRequired` or `Incompatible`,
provider ID, current/target schema IDs and a closed safe corrective code.
`MetadataSchemaRequest` selects `InspectOnly`, `CreateIfEmpty` or
`Upgrade(expectedCurrent,target,verifiedRecoveryPoint)`. Upgrades require
explicit host/operator authorization; no implicit `EnsureCreated`/`Migrate`.
`PrepareAsync` succeeds only when exclusive normal-use/upgrade admission and
all required checks are established. A store rejects ordinary operations until
admitted; metadata consumers cannot bypass the gate by obtaining its interface.

Private backup/restore tools implement the [recovery procedure](recovery.md);
there is no portable DDL, backup-file format or engine command in public APIs.
`MetadataAdministrationOptions` has a positive overall deadline, default
30 seconds and maximum two minutes, including exclusion, backup verification
and migration work; the same non-preemptible-call ownership rules apply.
The memory fixture advertises logical schema-state simulation only and cannot
produce a durable recovery point.

The host-side `IHoardModule` adapter registers store services in
ConfigureServices, opens/inspects/prepares only in InitializeAsync, reports
safe readiness, maps no metadata endpoint, and disposes via existing StopAsync/
lease ownership. F-03 supplies only owner-scoped options/secret references.
Provider packages themselves never reference Hosting to implement this adapter.
Missing mandatory interfaces/guarantees fail explicit fixture composition;
old marker-only providers remain valid for old declaration-only hosts.
