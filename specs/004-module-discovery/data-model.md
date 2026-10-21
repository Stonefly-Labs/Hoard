# F-04 Discovery Model

**Status**: Proposed immutable in-process model. No database/schema migration.
Wire names are defined in [OpenAPI](contracts/openapi.json); CLR spellings may
follow repository conventions without changing the agreement below.

## Distribution Catalog and Publication Policy

| Field | Meaning / invariant |
| --- | --- |
| Distribution ID/version | Explicit public host identity; not a filesystem path or arbitrary executable metadata |
| Inventory completeness | `complete` or `partial`; only complete records establish absence |
| Included declarations | Explicit positive records for included packages, including unregistered ones |
| Public module/field text | Explicit host-approved literals keyed to known declaration identities; no runtime/configuration values |
| Support records | Exact capability ID/version, operation ID, owner IDs and tested evidence IDs/scope |
| Binding associations | Required route responsibilities/methods or opaque service association IDs; no delegates on the wire |

Catalog identities are canonical, unique and bounded. A registered declaration
and included record for the same ID must agree on category/version; inconsistent
or duplicate catalog records fail discovery setup without choosing a winner.
Registration establishes positive knowledge for its own module, not inventory
completeness. A requested ID omitted from a partial inventory is unknown, not
absent. No invented absent module entry is returned as an installed module.

Catalog inputs are immutable arrays/closed records, not lazy callbacks.
Freeze before configuration evaluation/composition snapshots services. Later
mutation is rejected or cannot affect the frozen lifecycle.

## Module Entry

| Field | Meaning / invariant |
| --- | --- |
| `id`, `category`, `version` | Safe known declaration identity; no CLR type/assembly path |
| `inclusion`, `registered`, `enabled` | Independent positive knowledge, registration and fixed selection |
| `compatibility` | Declared host/abstractions ranges and prerelease flags; never a fresh validation result |
| `provenance` | Bounded declared classification plus approved public publisher, not certification or raw URLs |
| `lifecyclePhase`, `readiness` | From the captured lifecycle revision, with explicit disabled/initializing/not-ready/failed/stopping/stopped/unknown |
| `selectedRoles` | Metadata/artifact authority or selected identity, derived from validated fixed selection |
| `options` | Safe descriptive fields only, not operational settings or winning sources |
| `capabilities` | Scoped contributions; not a global union of capability names |
| `reasons` | Closed safe reasons for unavailable/unknown public metadata or state |

Included-but-unregistered entries have `registered=false`, `enabled=false`,
phase/readiness `unknown` and reason `missing-registration`, not unhealthy.
Registered-disabled entries have readiness `disabled`; no active-version,
secret, validator or readiness callback is introduced to describe them.
Unsupported future category/state strings are preserved only as safe descriptive
unknowns by the consumer and cannot authorize actions.

## Capability Contribution

Identity is the tuple `(capabilityId, capabilityVersion, operationId, ownerIds)`.
Owners are sorted canonical distinct IDs; overlapping contributions remain
separate. Emit a multi-owner contribution once under its first sorted owner;
other owners remain explicit references, not duplicate contribution entries.
Each contribution has distribution support (`supported`,
`unsupported`, `unverified`), evidence scope (`fixture`, `production`, `unknown`),
bounded evidence IDs, availability and safe reasons.

`usable` requires all of:

1. An exact host-approved implemented/tested support record, within its stated
   fixture/production scope.
2. Every owner and operation dependency present, enabled and compatible under
   the existing validated composition. Optional integrations require their
   target too; absence/disablement supplies no integration.
3. All required actual route/service bindings sealed for their correct owners.
4. Startup admission open, the host in a serving phase and the contributing
   owners/dependencies ready in the same captured observation.

An unrelated module's runtime readiness loss does not substitute for these
operation-specific checks; global readiness is still reported separately.
Stopping/stopped overrides a module's previously ready status. Initialization
or unknown evidence cannot yield usable. Lifecycle compatibility failures remain
startup failures, not discoverable supported-but-repaired compositions.

Availability is `usable`, `unavailable` or `unknown`. Support is independent:
a supported operation can be temporarily unavailable; an unverified declaration
never becomes supported through health. Availability grants no permission.

## Actual Composition Evidence

Route evidence identifies owner, responsibility and explicit methods, derived
from the existing sealed owned routes and final route validation. Do not publish
private handler delegates or arbitrary configured addresses.

Service evidence identifies owner and an opaque host public binding ID.
The exact service descriptor must have been added by that owner's supervised
ConfigureServices and remain the effective unkeyed single-service registration.
Shadowed/removed/wrong-owner descriptors provide no usable proof. Reject
unsupported keyed/enumerable ambiguity as unavailable, never resolve a service
or execute its factory to manufacture evidence.

Both ledgers are immutable after build/mapping. Host/provider endpoint mutation
after final validation is unsupported under the inherited lifecycle contract.

## Published Lifecycle State and Read Envelope

The coordinator publishes a single immutable internal reference containing:

- Composition/lifecycle identity, monotonically increasing revision, publication
  time, last completed readiness-assessment time (nullable before assessment).
- Phase, startup admission and aggregate readiness.
- Bounded per-module phase/status and closed safe diagnostic categories, not
  copied unbounded health arrays or provider text.
- Fixed catalog/composition/binding identities that cannot cross lifecycles.

Every discoverable transition publishes under the same existing state lock:
construction/service/mapping phases, initialization, committed readiness result,
worker failure, admission closure, stopping/drain/cleanup, terminal state and
late safe diagnostic updates. No request path acquires that lock. Publication
must not invoke observers, provider code, serialization or I/O under the lock.
An initial registered publication exists before activation.

The request captures one reference with acquire/release memory semantics.
`capturedAt` is the envelope capture time; `publishedAt` and
`readinessAssessedAt` describe authority observations, not refresh-time probes.
All derived module/global/capability fields use that one reference.
The public F-02 snapshot constructor and IHoardLifecycle interface stay intact.
Module phase means the last entered authority phase: a ready module may still
report `assessing-readiness` while the host reports `running`. Discovery must
not rewrite that distinction or mutate lifecycle state to simplify display.

Unknown/missing source returns explicit failure. A stopped publication may be
read in a fixture before disposal, but no stopped operation is usable. A failed
host is never started solely to expose its publication.

## Sanitized Option Description

Safe field identity, type, required/secret flags and numeric length/range
constraints come from matching known descriptor/configuration metadata.
Public text, ordinary allowed values and defaults require separate explicit
host approval, not regex filtering of provider strings. Secret fields have no
default/example/allowed values. Unsupported/unapproved descriptive material is
omitted with `metadata-suppressed`, not echoed or treated as valid settings.

Do not hold or serialize HoardModuleOptions, secret handles/references, raw
input/report objects, private paths, effective values or exception payloads.
The publication boundary is a reviewed disclosure allowlist, not an arbitrary
secret detector or protection against malicious trusted in-process code.

## Availability Explanation and Diagnostics

Each explanation has a closed reason code, fixed corrective template, approved
affected module/operation identity when available and optional random
correlation ID. Unknown input identities are omitted from affected-ID members
and represented by closed unknown-state reasons, never reflected query strings.
Unknown provider diagnostic codes
become `observation-unavailable`; approved existing codes may select a reviewed
template without copying the original record.

Reasons include missing inclusion/registration, disabled, unsupported,
unverified, dependency-unavailable, binding-unavailable, initializing,
not-ready, stopping, stopped, observation-unknown, metadata-suppressed,
observation-unavailable, deadline, response-limit and invalid-protection.
Reason ordering is deterministic; retain all applicable bounded reasons plus
omitted count rather than hide one failure behind a green aggregate flag.

## Consumer Observation State

The [presentation contract](contracts/presentation.md) defines loading, empty,
denied, failed, unknown and stale states, separate module dimensions and action
eligibility. Refresh generations reject late responses from older attempts.
The consumer's monotonic receipt-age limit is 30 seconds; a failed refresh
immediately makes retained data stale. Capture/publication/assessment times
remain visible; a new read does not imply a new assessment.

## Bounds, Cancellation and Ownership

Use the plan's finite collection/text limits. Invalid static catalog/options
fail before activation; encoded overflow or unavailable publication returns a
safe failed read, not a partial inventory. Capture/projection/encoding checks
cancellation and a monotonic two-second default deadline at least every 64
items and on bounded buffer writes. A capped 4 MiB private buffer is disposed
after sending or failure. No pooled buffer or HttpContext escapes the request.

The read creates no background task, observer subscription or provider resource.
Authentication/transport remain trusted host framework work and must cooperate
with cancellation; a bounded wait is not a kill guarantee. Do not duplicate
F-02's resource cleanup or dispose module/root resources from discovery.
