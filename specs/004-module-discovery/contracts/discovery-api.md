# F-04 Management Discovery HTTP Contract

**Status**: Proposed version 1 read contract, not implemented endpoints.
Machine-readable shapes: [openapi.json](openapi.json).

## Routes and Access

| Method / literal path | Successful response |
| --- | --- |
| `GET /api/v1/discovery` | Complete authorized discovery observation, `application/json` |
| `GET /api/v1/discovery/openapi.json` | Fixed protected OpenAPI 3.1 document, `application/json` |

Both endpoints enforce the same management-read policy and explicit
[exposure posture](hosting-api.md#exposure-and-authorization). GET is the only
supported method; HEAD is not implicitly advertised. No query parameters,
filtering, pagination, mutation/install/enable operation or public Swagger UI.
Unknown query parameters receive a generic safe 400 without reflected text.
Method mismatch uses ordinary framework 405 handling without inventory.

Successful and failed responses use `Cache-Control: no-store, private`,
`Pragma: no-cache`, `X-Content-Type-Options: nosniff`. Do not issue ETags/304s
or enable shared/proxy caching. No unauthenticated liveness response embeds
inventory or schema; no credentialed wildcard CORS configuration is introduced.
The later static console uses same-origin management access by default.

## Observation Envelope

| Member | Agreement |
| --- | --- |
| `schemaVersion` | Integer 1; major wire contract, distinct from module/platform releases |
| `distribution` | Approved ID/version and `complete`/`partial` inventory knowledge |
| `observation` | Lifecycle UUID, positive revision, captured/publication timestamps and nullable last assessment timestamp |
| `host` | Phase, aggregate ready and startupAdmission; no liveness inference |
| `modules` | Sorted complete bounded array of known safe entries, not partial pagination |
| `reasons`, `omittedReasonCount` | Closed safe aggregate diagnostic categories and explicit omitted count |

Module IDs are unique; sort modules by ID, capabilities by identity tuple and
options by field ID. Registration/selection/support/readiness are separate
dimensions. Selection roles identify the fixed authoritative metadata/artifact
and chosen identity schemes, not settings. Included-but-unregistered entries
remain non-enabled/unknown. Unknown inventory completeness cannot establish
absence. Failed startup uses existing local diagnostics, not a new service.

Each capability has exact ID/version/operation/owners/dependencies, support,
evidence scope/IDs, observed availability and reasons. Dependencies refer to
known safe module IDs; when a dependency cannot be safely identified, retain
the closed dependency reason, never arbitrary source text. Do not publish
Type names, delegates, service keys, private route URLs or secret locators.

Sanitized options contain only descriptive approved fields. Numeric constraints
and explicitly approved public ordinary defaults/allowed literals are permitted.
Secret fields contain no default, example or allowed literals; examples never
show configured values or reference targets. Descriptions are inert plain text.
The public disclosure allowlist is separate from provider metadata trust.

## Failure Responses

| Status | Meaning / disclosure |
| --- | --- |
| 400 | Unsupported query/input shape; generic safe category, no reflected input |
| 401 | Unauthenticated network access; normal challenge, no inventory |
| 403 | Authenticated caller without read permission, or rejected local/proxy request; no inventory |
| 503 | Protection not verified, observation unavailable, internal inconsistency, deadline or size bound exhausted; closed safe problem |

Use `application/problem+json` for owned non-challenge failures:
`type` is fixed `about:blank`, `title`/`detail` are host templates, `status` is
the real status, `code` is a closed reason, `phase` is a closed read-phase
category (including `unknown`) and `correlationId` is random. Optional `moduleId`
and `operationId` retain only approved affected identities where known.
Never include raw request path/query or exception text in an `instance` member.
401/403 challenge responses may have an empty body; if a problem is emitted it
uses this same safe shape. A disconnected/canceled caller need not receive a
body; abort/cancellation must not be logged or counted as a successful read.
If cancellation occurs before response dispatch, do not commit a 200.

The two-second default compute/encode deadline precedes successful headers.
Encoding checks actual UTF-8 bytes against 4 MiB, not only character counts.
No partial array, empty-success fallback or stale server cache is returned.
Network delivery/authentication cooperation is not a preemptive timeout claim.

## Freshness and Consumer Compatibility

The captured immutable lifecycle revision is the authority for every state
and derived availability field. `capturedAt` records retrieval; `publishedAt`
records the last lifecycle publication; `readinessAssessedAt` is the last
completed inherited assessment. A fresh GET does not run an assessment, imply
continuous monitoring or guarantee future operation success.

Version-1 consumers ignore unknown additive descriptive fields, but never
interpret an unknown operation, enum/state meaning or schema version as
eligible. Required-field/type/identity mismatch is an incompatible response,
not empty success. Unknown states preserve safe recognized inventory as
unknown; a malformed envelope fails the read. Duplicate module/contribution
identities are invalid, not last-write-wins.

Per [presentation rules](presentation.md), refresh failure immediately marks
retained information stale; receipt age beyond 30 seconds also expires action
eligibility. Generations prevent old refreshes or old lifecycles from replacing
newer accepted data. Availability never grants execution authorization.

## Description and Public Compatibility

The protected OpenAPI document is fixed per deployed Application version; it
contains no distribution-specific inventory. It explicitly describes both
routes, access, no-cache and safe errors. Deployment cannot expose a second
anonymous static copy or development documentation bypass.

The document's `x-hoard-required-policy`/exposure extensions describe the
host-provided access contract without inventing a bearer/cookie credential
format or production identity scheme. Standard OpenAPI tooling does not enforce
those extensions. Their presence, or the absence of a concrete security scheme,
never relaxes endpoint authorization; a composed host must document its actual
credential integration separately.

Implementation must compare emitted DTOs and the deployed embedded document
against [openapi.json](openapi.json), including required properties, enum
meanings, examples, failure shapes and encoded limits. Additive optional
descriptive fields are wire-compatible; deleting/renaming required fields,
changing types or existing state meanings requires a new major route/schema.
Unknown newly added states remain fail-closed for older clients. Module/
abstractions SemVer policy remains independent and unchanged.
