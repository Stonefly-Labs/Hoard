# F-06 Publication, Recovery and Deletion Protocol

**Status**: Planned qualification mechanisms, not a production recovery tool.
Read with [API](artifact-api.md) and [model](../data-model.md).

## Local Qualification Configuration

Use one owner-private root on an actually reported local filesystem; staging,
immutable data, decisions and operation records share that filesystem.
Initialization explicitly chooses create-empty or reopen-compatible. A missing,
corrupt, foreign or incompatible root cannot be silently reset. Acquire exclusive
process/session ownership before opening records; a second process fails admission.
Do not treat an abandoned lock filename as evidence that the OS ownership is free.

Root paths come only from trusted owner-scoped configuration, never package
input. Derived paths use validated fixed digest/ID components; no caller locator
is concatenated. Reject symlink/reparse entries, escaping ancestors, foreign
handles and cross-volume staging. The root and parents are not attacker-writable;
arbitrary same-privilege external writers are outside trusted in-process scope.
Tests still inject malformed/foreign/symlink paths and require safe refusal
without touching an outside sentinel.

A private versioned/checksummed format holds issued tickets/intent, owner
generation/expiry, immutable data and a per-digest current/tombstone decision.
All state sizes and object counts are bounded. Corrupt format/checksum blocks
admission with a safe code; recovery preserves evidence rather than guessing.
This private format is fixture-local, not a stable interchange format or schema
migration product.

## Local Commit and Reconciliation

1. Flush the issued ticket/intent before admitting source I/O. Allocate a unique
   staging owner/generation and byte reservation. Incomplete state is private.
2. Stream and hash to EOF. Write/flush a verified-stage record only after exact
   expectations match; check owner again at this decision.
3. Acquire shared publication authority, then the provider's digest decision
   gate. Recheck current owner/expiry and existing content. Under exclusive root
   ownership, publish only fully flushed immutable payloads; no reader follows
   staging or a partially copied destination.
4. Flush intent for the decision, then atomically replace/create the small
   same-filesystem current decision pointing to the complete incarnation.
   Include ticket and immutable identity. This is the visibility decision.
   No cross-volume copy fallback or overwrite of a valid different incarnation.
5. Finalize/flush the ticket receipt before success. Open/verify direct content
   availability; if verification or acknowledgment is lost, return uncertainty
   or corruption, never a success-shaped hit.
6. Release publication protection only after the decision is definitely settled.
   Remove only the completed ticket's residual staging through bounded cleanup.

The digest gate/session root ownership, not `File.Move(overwrite:false)` alone,
supplies conditional semantics. Payloads never change in place. Reused content
gets its own operation receipt but retains its existing incarnation.

After interruption, recover exact pending intents against direct decision
records before ordinary mutation/read admission. A matching published decision
plus complete verified payload finalizes `Committed`; a definitely unentered
decision finalizes `NotCommitted`. Corrupt/inconsistent/unknown records remain
explicitly blocked/uncertain, never presumed absent. No later mutation can
replace an unresolved decision until its receipt is durable, preserving
reconciliation after later delete/recreate. Retain receipts for 24 hours;
after expiry refuse replay even if the digest happens to exist again.

An acknowledged artifact survives qualified abrupt process termination. Flush
calls do not prove directory/power-loss/device durability; the exact OS,
filesystem, runtime, flush configuration and crash model accompany every result.
No OS reboot, power-cut or remote filesystem claim follows from these steps.

## Required Abrupt-Stop Boundaries

The parent starts a known child in a fresh private root and waits for a
machine-readable named barrier; it kills only that PID without graceful stop,
waits for actual signal exit, then reopens with a fresh process. Exceptions,
cancelled tasks and simulated fault flags are not crash evidence.

| Barrier | State when stopped | Required reopened observation |
| --- | --- | --- |
| B0 staging | Prefix written, no verification | No committed prefix; acknowledged control artifact intact |
| B1 verified | EOF/hash flushed, no visibility decision | No committed new artifact; expired old owner fenced |
| B2 published | Decision/direct bytes present, acknowledgment withheld | Reconcile exact ticket once; complete identity/length, no duplicate effect |
| B3 acknowledged | Success durably recorded and observed by parent | Complete content survives; identical receipt on retry |
| D0 removed | Logical tombstone committed, acknowledgment withheld, payload retained | No new open; reconcile removed/pending-reclamation; no deletion of later incarnation |
| D1 reclaimed | Exact payload removed, acknowledgment withheld | Same logical removed result, repeated cleanup harmless |

Each run seeds previously acknowledged content and verifies its entire bytes
after reopening. Record child PID, barrier/run ID, signal, state hashes, receipt,
readback digest/length and exact environment. Missing/wrong barrier or kill
failure fails the case; no sleep-based inference. D0/D1 additionally reopen,
publish identical bytes as a fresh incarnation and apply stale deletion/cleanup.

## Staging and Maintenance Ownership

Acquire/renew/release checks ticket, session, owner and generation at every
state decision. Equality with expiry is expired. Renewal and cleanup serialize
the expiry decision; once renewed, an earlier cleanup candidate cannot win.
Renew at ten-second intervals only while admitted active work remains inside its
total deadline; a stalled native call cannot keep a mutation eligible forever.

Restart fences prior session generations before reusing a ticket. Resuming an
unfinished live ticket allocates a new owner and revalidates any retained staged
bytes before commit; malformed/incomplete stages must be restaged and verified.
Expired/replaced owners cannot append, renew, commit, abandon or remove new work.
Persist expiry decisions/time floors so wall-clock rollback does not revive them.
No distributed lease, multiple hosts or clock-synchronized HA is implied.

Recovery observes at most 100 typed rows per page with explicit continuation and
listing consistency. Cleanup checks at most 100 exact candidates in one finite
call and returns completed/conflicted/pending work and continuation. Restarting
cleanup is harmless; missing listing entries never establish absence. Active
work, unknown state and committed unreferenced content are not reclaimed as
abandoned staging. Committed observations can be passed to shared reconciliation,
but cannot manufacture cache entries or authorize eviction.

## Deletion and Physical Reclamation

1. Reserve a ticket for the exact observed stamp.
2. Ask the shared authority for exclusive deletion. Block new shared admissions,
   wait for current readers/publication/metadata guards and obtain a current
   authoritative zero-reference observation. Missing/unavailable authority denies.
3. Under the provider decision gate, validate epoch/incarnation and current grant.
   Record mutation intent, then a logical tombstone bound to the ticket/stamp.
   From that decision, new opens fail; release exclusion only after outcome
   definitely settles, not merely when the initiating caller stops waiting.
4. Record `Removed(ReclamationPending)` durably before optional physical
   removal. Reclaim only that incarnation; finalize physical status when known.
   A failed unlink/delete reports pending/failed capacity reclamation without
   claiming freed bytes. Committed logical absence remains truthful.
5. Repeated cleanup/reconciliation cannot delete a new incarnation. Same-ticket
   retry returns its original logical receipt; physical status may advance from
   pending to reclaimed under the same receipt identity. Fresh old-stamp requests
   return already absent only while no new incarnation exists.

Metadata publication, reference admission and physical removal share one guard
protocol. A zero-reference check performed before exclusion or a stamp alone is
not authority. A read still running at expiry retains protection, so deletion
cannot truncate it. If uncertain local/native work cannot settle, deny new
admission and report incomplete cleanup rather than releasing guards unsafely.

## Alternative No-Rename Fixture

Implement this package independently: private multipart pieces, immutable
completed object, versioned conditional visible pointer and conditional
tombstone. No call to filesystem rename or local-journal helper may implement
its publication/deletion decision. Disk scratch is only a bounded payload
mechanism, not a claim of durable object service.

Controlled barriers independently delay completed-object direct availability
and pointer/list enumeration. Commit success requires direct exact content
visibility before budget expiry; timeout after a conditional pointer decision
is uncertain and reconcilable, never a miss. Conditional version comparison
rejects stale publication/deletion even when enumeration is delayed.
Multipart cleanup fences expired owners and cannot remove finalized/new objects.
The same consumer/cases exercise delayed listing, conditional races, active
readers, corruption and pending reclamation. Durable restart cases explicitly
do not apply; no remote vendor or account is qualified.

## Reproducible Recovery Walkthrough (After Implementation)

1. Run the full [quickstart](../quickstart.md) in a fresh owner-private
   destination with sufficient local space. Preserve its manifest/configuration.
2. Select the local provider and seed a known acknowledged control blob; record
   stamp, digest, length, ticket and complete readback.
3. Run B0..B3, D0..D1 separately with parent/child handshakes above. Reopen each
   exact root only after the original process exited and root ownership is free.
4. Inspect the exact ticket, current decision and complete read result; compare
   with each barrier's expected outcome. Never replay uncertainty under a new ID.
5. Page observations and renew a live owner while an old cleanup candidate is
   paused; release barriers and require only abandoned exact generations removed.
6. Demonstrate commit with deliberately failed metadata publication: no cache
   entry is fabricated, the blob remains directly identifiable, and shared
   reconciliation can later decide its treatment under current authority.
7. For logical deletion, inspect pending versus confirmed reclaimed status.
   Recreate the digest and prove old tickets/cleanup cannot remove its new stamp.
8. Retain safe report/hashes outside Git. Inspect corrupt state without repair;
   restoring/reinitializing a root or changing format requires explicit operator
   action and compatible tooling, not automatic downgrade/reset. Production
   backup/disaster-recovery tooling remains separately scoped.
