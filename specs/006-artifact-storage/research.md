# F-06 Research and Decisions

**Date**: 2026-10-22. Design research only; no storage qualification ran.

## Repository Evidence and Integration

- [Provider marker](../../src/Hoard.Abstractions/Providers/IArtifactProvider.cs)
  is declaration-only. Add operations separately, preserving old implementations.
- [Existing digest](../../src/Hoard.Abstractions/Metadata/MetadataValues.cs)
  validates exactly 32 SHA-256 bytes/lowercase hex. Reuse it, not a competing
  digest/parser or breaking namespace move.
- [F-05 publication authority](../../src/Hoard.Abstractions/Metadata/IMetadataPublicationAuthority.cs)
  already holds committed-artifact protection through metadata settlement.
  Its opaque evidence and digest/length record are enough for a host-side
  F-06 bridge; no metadata schema/API mutation is needed.
- [Metadata operations](../../src/Hoard.Abstractions/Metadata/MetadataOperations.cs)
  include `ConfirmUnreferenced` with a reference revision. That observation
  does not protect readers or issue deletion authority.
- [Architecture](../../docs/ARCHITECTURE.md) and
  [ADR-0001](../../docs/adr/0001-modular-provider-architecture.md) assign
  mechanisms to providers and shared correctness/coordination to Core.
  F-06 uses a controlled host authority fixture, not a second cache engine.
- Existing build policy targets nullable .NET 10, warnings as errors and
  tracked locks. Existing acceptance isolates independent package consumers,
  retained binaries and owned child processes. No new dependency is necessary.

## D1: Additive BCL Operations and Explicit Trust

**Decision**: `Hoard.Abstractions.Storage` owns new operation/value contracts.
Keep `IArtifactProvider`, F-01 declarations and F-02/F-03/F-05 APIs unchanged.
Use the historical `Metadata.ArtifactDigest` in the new identity value.
The selected store is injected once; opaque handles are trusted in-process
references, not authentication credentials or HTTP tokens.

**Rationale**: Small compatible addition with no SDK or database leak.
Provider ID, store epoch, digest, length and incarnation have separate roles.

**Alternatives considered**: Extending the marker breaks retained providers;
moving the digest breaks public source/binary compatibility; accepting raw paths
or using package coordinates as content identity violates confinement/isolation.

## D2: Verify Once Per Submitted Stream, Again for Reuse and Read Completion

**Decision**: Stage with fixed buffers and incremental SHA-256 plus an optional
explicit SHA-512 expectation. Require EOF and exact length; never infer EOF
from a short read. Rehash existing bytes before successful reuse, and every
full read while copying. Copy completion, not open, establishes verified read
success. Corruption marks the incarnation unusable until explicit recovery.

**Rationale**: Neither a digest filename nor old commit evidence proves today's
bytes. Caller-supplied expectations never substitute for computed identity.
Streaming read errors may leave partial destination output; callers must reject
it, and future protocol code cannot turn it into a completed hit.

**Alternatives considered**: Buffered whole-artifact verification breaches the
memory bound; checking only expected length misses extra input; trusting an
existing file or capability declaration allows corrupt deduplication.

**Primary sources**:
[Stream.ReadAsync](https://learn.microsoft.com/dotnet/api/system.io.stream.readasync?view=net-10.0),
[IncrementalHash](https://learn.microsoft.com/dotnet/api/system.security.cryptography.incrementalhash?view=net-10.0).

## D3: Process-Crash Durability Is Not Power-Loss Certification

**Decision**: The local fixture owns an exclusive private root, stages on the
same filesystem, flushes verified bytes and decision/receipt files, and uses
atomic namespace decisions under owned exclusion. Qualify abrupt process
termination on the observed OS/filesystem. Do not claim OS-crash, power-loss,
device-loss, cross-volume or network-filesystem durability.

**Rationale**: File flush and namespace durability are distinct. A portable
BCL file flush does not certify directory-entry persistence or storage firmware.
No new native interop is required for this bounded process-failure claim.
`File.Move` is a mechanism, not a universal conditional-create primitive.
Independent writers/external file modification are outside admitted root
ownership; corruption is still detected and fails closed.

**Alternatives considered**: Temp copy to final name exposes incomplete bytes;
assuming `overwrite:false` provides the full concurrent contract ignores
platform/runtime differences; platform-specific directory flushes and power-cut
rigs exceed F-06's declared qualification model.

**Primary sources**:
[File.Move](https://learn.microsoft.com/dotnet/api/system.io.file.move?view=net-10.0),
[FileStream.Flush](https://learn.microsoft.com/dotnet/api/system.io.filestream.flush?view=net-10.0),
[RandomAccess.FlushToDisk](https://learn.microsoft.com/dotnet/api/system.io.randomaccess.flushtodisk?view=net-10.0),
[Linux rename](https://man7.org/linux/man-pages/man2/rename.2.html),
[Linux fsync](https://man7.org/linux/man-pages/man2/fsync.2.html),
[Apple fsync](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html).

## D4: Ticketed Decisions, Incarnations and Bounded Ownership

**Decision**: Persist issued tickets/intent before mutation. Bind decisions to
store epoch, ticket, immutable request fingerprint and incarnation. Recover
unfinished decisions before normal admission; reconcile by exact ticket/direct
decision, never by incomplete listing. Retain receipts 24 hours, then refuse
automated replay. Fence staging generations at expiry, replacement and restart.

**Rationale**: A timeout after namespace change cannot prove rollback. Digest
reuse after deletion needs a new incarnation even for byte-identical content.
Bounded tickets, staging capacity, pages and timeouts prevent hidden work growth.

**Alternatives considered**: A bare idempotency string cannot distinguish an
unknown/expired operation from a never-executed one; regenerating a ticket on
uncertainty allows unsafe duplicate effects; deleting only by digest has ABA races.

## D5: One Authority for Metadata Admission, Readers and Deletion

**Decision**: HostAdapters owns one store-scoped authority with fair shared
protection for readers/publications/references and exclusive deletion. It
bridges the existing F-05 publication seam, revalidates store evidence and
metadata reference state, and retains exclusion through uncertain settlement.
Providers receive this authority at initialization, never per caller.

**Rationale**: Metadata-only zero references, a time-limited token or a boolean
`safeToDelete` cannot exclude concurrent new references/readers. Store-private
decision locks serialize conditional changes, but do not replace shared policy.
No external authority call is made under a provider's internal state lock.

**Alternatives considered**: Provider queries of SQLite private tables violate
neutrality; duplicating reference policy in each store violates shared ownership;
releasing a delete guard on caller timeout permits stale removal of new content.

## D6: Cooperative Streaming and Truthful Late-Work Ownership

**Decision**: Qualified input/destination streams honor asynchronous cancellation.
Use total and inactivity budgets with bounded worker slots. Never close borrowed
streams to force cancellation. A non-cooperative I/O negative proves explicit
incomplete cleanup, fenced mutation, retained resources and blocked admission.

**Rationale**: Cancellation is cooperative; racing a wait timeout cannot stop
arbitrary user code or native I/O. Dispose/cancel under live work can corrupt
ownership. Finite release claims apply to the qualified cooperative profile,
not a device/stream that never returns. An implementation unable to meet that
profile cannot advertise conformance.

**Alternatives considered**: `Task.Run` per chunk, detached work, forced thread
termination and disposing caller streams are unsafe/unbounded shortcuts.

**Primary source**:
[Cancellation in managed threads](https://learn.microsoft.com/dotnet/standard/threading/cancellation-in-managed-threads).

## D7: Independent No-Rename Object Semantics

**Decision**: A separate test package implements private multipart parts,
final immutable payloads and conditional versioned pointers without rename.
Delay direct visibility and listing independently; wait/probe direct visibility
before commit success, or return uncertainty. Disk-backed payloads allow the
same real large-transfer cases without an in-memory multi-GB artifact.

**Rationale**: Logical portability must not be a second wrapper around the
local journal. An opaque object version is not a content digest; listing
absence never proves direct absence or gives deletion permission.

**Alternatives considered**: An in-memory dictionary of full payloads breaches
SC-002; reusing the local adapter does not prove independence; a real cloud
service adds account/SDK/service scope without qualifying other services.

**Primary source**:
[RFC 9110 conditional requests](https://www.rfc-editor.org/rfc/rfc9110.html#name-preconditions)
provides generic `If-Match`/`If-None-Match` semantics, not a vendor guarantee.

## D8: Actual Resources and Attributable Evidence

**Decision**: Each provider's 256 MiB/4 GiB child uses generated, non-seekable,
paced content, hashes readback and measures incremental peak process RSS.
Separate real OS-killed local children prove each durable boundary. Exact
provider/case inventory, hashes, signals and environment are required for a
qualification result; selected phases always report nonqualification.

**Rationale**: Managed allocation counters, test names, synthetic exceptions
and old artifacts are not proxies for RSS, crash survival or current behavior.
Full qualification fails rather than skips missing space/platform support.

**Alternatives considered**: A smaller payload, mocked counter, subprocess exit
alone or another provider's proof cannot meet the stated outcomes.
