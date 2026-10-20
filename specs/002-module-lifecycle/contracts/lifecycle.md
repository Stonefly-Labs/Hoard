# F-02 Lifecycle, Route and Admission Contract

**Status**: Planned operational behavior, not implemented evidence.
Inputs and states are defined in [data-model.md](../data-model.md);
library entry points are in [public-api.md](public-api.md).

## Ordered Startup

1. Snapshot registrations, adapter associations, explicit selection, platform
   versions and finite budgets. Validate all declaration structure/identity,
   then selected platform/dependency/capability/cardinality rules. No module
   constructors, callbacks, service factories, probes, or external I/O.
2. Compute prerequisite-first order using ordinal smallest-ready-ID ties.
   Begin a single lifecycle lease and startup deadline. Record each entered
   module before inert adapter construction and ConfigureServices. Reject
   independent module hosted workers. Do not build a temporary DI container.
3. Call `BuildHoardApplicationAsync` once, not bare `builder.Build()`. The
   composition lease owns and supervises the build task against the existing
   startup deadline, rejects a late poisoned result, and retains root disposal
   ownership even before any framework hosted service could run.
4. Map enabled adapters' owned routes, finalize data sources and reject
   ambiguous ownership/unsupported shapes. Install admission protection before
   host start. Mapping must complete before initialization and before traffic.
5. Initialize enabled adapters in the validated order, awaiting completion
   before any dependent. Any failure, cancellation or timeout stops the sequence.
6. Assess every selected module's explicit readiness and required declared
   health responsibilities. A false/missing/failed/timed-out result fails
   startup; explicit enablement is never degraded optional startup.
7. Under the coordinator's state lock, verify no stop latch and publish startup
   admission/ready state. Only then dispatch tracked worker tasks and allow
   normal module requests. A worker launch fault fails the lifecycle and
   closes admission; a no-worker completed task is valid.

The Generic Host bridge invokes the coordinator but is not the source of
module ordering guarantees. Readiness is not process liveness, and no diagnostic
or health HTTP surface is automatically made public.

## Owned Routes

F-01 endpoint declarations remain descriptive. Each enabled adapter maps actual
routes through the Hosting builder, tagged with its safe owner and a declared
endpoint responsibility. The builder alone owns matching metadata and data
sources. Every declared responsibility must be represented; no mapped endpoint
may use an undeclared responsibility.

Initial supported route language:

- Absolute `/`-separated paths with literal segments and required unconstrained
  whole-segment parameters such as `/fixture/{id}`. Parameter names are unique
  within a pattern and do not affect ownership equivalence.
- Explicit nonempty sets of standard HTTP methods (GET, HEAD, POST, PUT, PATCH,
  DELETE, OPTIONS, TRACE, CONNECT), normalized uppercase without duplicates.
  HEAD must be explicitly declared; a methodless/all-method endpoint is rejected.
- Framework default order only; no optional/default/complex/constrained/
  catch-all segments, fallback endpoints, custom matching policies, host-based
  route constraints, dynamic sources, or routing-affecting caller conventions.
  Parse failures and unsupported constructs fail startup explicitly.

Use framework parsing/precedence rather than a hand-rolled string key. Within
this language, path intersection requires the same segment count and compatible
literal positions (literal comparisons follow routing's case-insensitive
semantics; a parameter accepts either literal). Normalize root and trailing
separator equivalence according to actual framework matching. Two endpoints
are ambiguous only if their method sets intersect, their supported path
languages intersect, and their framework priority is equal. Different
parameter names never disambiguate. Different literal/parameter specificity
may give a unique winner and is allowed; registration order never does.

Check all finalized owned endpoints, including same-owner ambiguity, and any
host endpoints admitted into this route boundary. Unowned endpoints whose
pattern/matching metadata cannot be analyzed in this boundary fail startup;
do not silently exclude them. Keep diagnostic/liveness routes separate only
with an explicitly disjoint literal namespace validated against module routes.
F-02 supplies no such routes itself.

Examples: GET `/fixture/{id}` and GET `/fixture/{name}` conflict; GET
`/FIXTURE/{id}/` conflicts under equivalent slash semantics. GET and POST of
the same pattern are allowed; `/fixture/fixed` and `/fixture/{id}` are allowed
because literal precedence selects a unique endpoint. Disabled claimants are
never mapped or compared. Unsupported but potentially unambiguous arbitrary
constraints fail as unsupported, not as proven ambiguous.

This deliberately bounded API must document its limits. Later protocols may
extend the language with positive/negative overlap proofs; they must not bypass
the ownership gate or present unsupported routing as operational.

## Admission and Readiness After Start

Maintain two separate signals: startup admission and current aggregate
readiness. Before successful complete startup, requests to mapped normal module
routes receive safe 503 and ongoing worker callbacks do not start. Disabled
routes do not exist. Startup and stop transitions are serialized with admission
so there is no publish-ready-after-stop race.

After startup, `AssessReadinessAsync` evaluates enabled modules with a single
finite assessment deadline; disabled modules receive zero probes. Required
health responsibility omissions and invalid probe output are failures.
Concurrent assessments share one in-flight task so stale completions cannot
overwrite newer stop/failure state. Cancellation of a caller's wait does not
turn shared state into ready or cancel another caller's assessment.

A later not-ready state changes aggregate readiness with safe owner/reason;
successful reassessment may restore it for the identical selected composition.
It does not auto-restart/replace modules or close admission/drain existing
traffic merely because health changed. Existing handlers remain responsible
for safe operational errors and centralized auth/cache boundaries. Stop or
worker failure closes admission permanently for this lifecycle.

## Stop, Drain and Cleanup

Latch stop atomically, make readiness false, close new module request and worker
admission, cancel the shared initialization/worker token, and prevent dispatch
of any further startup phase. Track admitted request/worker activity and allow
cooperative completion within the drain sub-budget, capped by remaining stop
time. New requests receive safe 503; no new worker callback may be admitted.
The worker admission unit is the single `RunAsync` callback, not each internal
iteration. Stop dispatches no new worker callback; an already admitted worker
task receives cancellation and its remaining execution is in-flight activity.
There is no atomic per-iteration promise for arbitrary trusted provider code.

Attempt stop for every constructed/entered adapter in reverse validated order,
including the adapter whose service/map/init callback failed. Keep successfully
initialized dependencies alive while dependent cleanup is still executing,
including after its coordination wait times out; an attempted callback is not
necessarily quiescent.
Only entered modules need cleanup; a failed inert constructor has no returned
adapter, and must release its own pre-return allocations.

Each adapter's StopAsync is attempted at most once with a linked cancellation
token and the smaller of its cleanup sub-budget/remaining overall stop time.
Record Completed, Failed or TimedOut accurately; continue to other eligible
adapters after an error. If the overall deadline expires, explicitly record
NotAttemptedBudgetExhausted for remaining entries. Preserve the primary startup
failure separately from additional cleanup errors.

Record each StopAsync task as pending Phase activity before dispatch; Phase
explicitly includes cleanup callbacks. A TimedOut wait does not remove a
still-executing callback from that activity or release its resource leases.
Preserve its TimedOut outcome, mark affected prerequisite omissions
UnsafePendingCallback and root disposal NotAttemptedUnsafe while it remains
active, and continue independent eligible cleanup within the same outer budget.
For A depending on B and unrelated C, a barrier-held timed-out A.StopAsync
protects A/B/root while quiescent C may clean up. A receives no second attempt.
If safe completion is observed before the shared stop operation ends, remaining
cleanup still uses the original deadline; no new cleanup round or budget begins.

Do not run cleanup concurrently with a still-executing activation callback,
cleanup callback, worker, or admitted request that could use the same resources.
Outstanding requests retain their owner's resource lease after drain expires,
including streaming response-body completion, not just handler return. Mark the owner
UnsafePendingCallback (with safe activity kind Request, Worker, Build or Phase)
when cooperative quiescence failed. Independent safe cleanup may still run.
A prerequisite whose dependent is still using it is also unsafe to release;
propagate this classification along active edges. This is explicit incomplete
cleanup, not silence or successful stop. Eventual task faults are observed
through safe categories, with no raw payload. No lifecycle instance is reused.

DI-owned services retain DI disposal ownership; adapters must not dispose them
twice. Adapter-owned operational resources are tracked and released by its stop
callback. The composition lease owns the built application and invokes root
host/provider disposal only after module cleanup and global quiescence. If any
request, worker, build or activation remains active, record root disposal
NotAttemptedUnsafe; this also applies to any still-executing StopAsync, even
after its wait was recorded TimedOut. This retains resources rather than
disposing them underneath in-flight work, and requires process-level recovery
if it cannot quiesce.
Supervise eligible root disposal with remaining shutdown time; a timeout is
explicitly incomplete, not guaranteed termination of arbitrary disposal code.

After the shared stop result is returned, observe late cleanup completion/fault
through safe categories only. Do not rewrite the returned TimedOut/unsafe
outcomes, retry stop, or launch deferred prerequisite/root disposal. An
incomplete terminal lifecycle retains the documented process-recovery boundary.

## Budgets and Non-Cooperative Code

| Budget | Default | Enforcement |
| --- | --- | --- |
| Overall startup | 120 seconds | Absolute deadline from first adapter construction, including service/build/map/init/readiness time |
| Activation callback | 30 seconds | Each constructor/composition/initialization callback; capped by startup remainder |
| Readiness assessment | 5 seconds | Whole aggregate assessment, also capped by startup remainder during first start |
| Overall shutdown | 30 seconds | One deadline for cancellation, drain and cleanup, never reset per module |
| Drain | 10 seconds maximum | Sub-budget; preserve remaining stop time for cleanup |
| Per-module cleanup | 5 seconds maximum | Sub-budget capped by overall remaining stop time |

Configuration must supply positive finite durations; no infinite sentinel or
zero success path. Inject `TimeProvider` for deadline calculations/testing.
Startup includes time between composition, host build and bridge start; a caller
that pauses too long must receive an expired-start result rather than a fresh
budget. Host integration must supervise host build and synchronous composition
as well as async hooks; a bare cancellation token does not bound a synchronous
call. Run potentially blocking callbacks under supervised tasks, keep mutable
composition unpublished until completed, and abandon a poisoned build/router
on timeout rather than reuse it while background code may still mutate it.
The explicit build extension, not `await using` alone, supervises synchronous
host build. A pending build protects all potentially used adapter/root resources
from concurrent cleanup; a late application is never returned to the caller.

The public promise is finite *coordination waiting*, not forced execution
termination, guaranteed in-process disposal, or crash cleanup. A non-cooperative
provider/DI factory/disposer can continue after the result; report it incomplete,
never forcibly abort a thread, and document explicit process termination/restart
as recovery. Constructor failures/late completions cannot publish readiness
or unpoison an instance. No successful resource release is inferred from
cancellation delivery alone.

## Concurrency and Diagnostics

Concurrent/repeated starts share the same start outcome; concurrent/repeated
stops share one stop outcome and cleanup ledger. Start after failure/stop is a
terminal-state error. Stop wins over readiness/initialization completion,
including a stop arriving immediately before admission publication.

Platform-owned error codes cover malformed registry, unknown selection,
cardinality/family mismatch, unsupported platform/dependency/capability,
cycle, missing adapter, unsupported/ambiguous route, phase failure,
cancellation, timeout, invalid readiness and incomplete cleanup. Diagnostics
include safe owner, phase, constraint/path, fixed corrective action and
correlation ID. Never attach a raw exception/inner exception or configuration.
Use registration ordinal references for unsafe identities; bound messages to
512 characters, paths to 32 IDs and diagnostic collections to 100 entries with
an explicit omitted-count marker. Longer inputs are rejected structurally,
not echoed. Descriptions/provenance URLs/provider text are never copied into
normal failure results or logs.

## Restart and Recovery

Selections and adapters are fixed for the lifecycle. Mutating the caller's
original selection has no effect; requesting an in-place replacement fails.
Choose another bundled/registered compatible module by creating a new host
with a new explicit selection. Adding an absent module requires a package
reference, registration/adapter, rebuild, redeploy and restart.

An invalid replacement fails without reverting automatically. Recovery means
explicitly restore the previous coherent package/selection set and start a new
instance. Lifecycle stop releases resources; it does not roll back provider
schemas, data, migrations, or partial persistent transactions.
