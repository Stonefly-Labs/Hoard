# F-04 Hosting and Application Integration Contract

**Status**: Proposed additive APIs; none exists yet. Names below fix the design
boundary and responsibilities, not a claim of released packages.

## Compatibility Boundary

Leave ModuleDescriptor, registration/provider markers, IHoardModule,
IHoardLifecycle, existing snapshot constructors, configured proof/owner inputs
and all compose/build/map/start/stop signatures unchanged. Do not add required
members to provider contracts. Preserve registration-only and discovery-free
F-02/F-03 behavior, existing ownership, admission and late-fault diagnostics.

Application may add its approved Hosting and ASP.NET Core framework references.
Its package must propagate those dependencies/framework requirements, including
for non-web consumers. Verify declared, resolved, packed and compiled graphs.
Metadata/artifact packages remain Abstractions-only; Core never depends on
Application, Hosting, EF Core or concrete providers.

## Proposed Opt-in Surface

| Surface | Agreement |
| --- | --- |
| `AddHoardDiscovery(HoardDiscoveryCatalog catalog, HoardDiscoveryOptions options)` on HoardBuilder | Record/freeze metadata and safe-source factory before evaluation/compose snapshots services; no callback, provider construction, container build or I/O |
| `HoardDiscoveryCatalog` | Immutable public distribution identity, inventory completeness, inclusion/publication/support/binding associations; no runtime input values |
| `HoardDiscoveryOptions` | Explicit exposure mode, existing management-read policy name, finite limits/deadline and trusted time source; unconfigured exposure fails |
| `IHoardDiscoverySource.Capture(CancellationToken)` | Bounded synchronous capture/projection of one internal immutable publication; returns closed success/failure and safe model, no provider/secret/probe access |
| `HoardDiscoveryReadResult` | Success observation or closed failure reason/correlation, never partial-success arrays, private inputs or raw exceptions |
| `BindHoardDiscovery(WebApplication application)` on HoardServiceComposition, implemented in Hosting | Verify the exact application retained by this lease and the source's composition/root/catalog identity, then return only IHoardDiscoverySource; foreign app/lease/source fails with a safe StaleComposition error |
| `MapHoardDiscovery(HoardServiceComposition composition)` on WebApplication, in Application | Verify same app/lease/source, map two protected literal GET endpoints before owned-route validation; add no services or listener |

Concrete read/source constructors are internal where ownership matters.
The source is a singleton bound to exactly one composition/root and its frozen
catalog; no static process-global current lifecycle or mutable multi-host cache.
Do not make arbitrary async source callbacks part of this public API.
The Application wire DTOs remain separate from Hosting's safe immutable model.
Application may read the same root's frozen HoardDiscoveryOptions for its
server-side policy name and encoding limits; these are never serialized as
deployment inventory or effective provider settings.

Application calls the public Hosting-owned BindHoardDiscovery guard rather than
accessing internal Application/Composition/Coordinator members or merely finding
a matching lease in DI. Hosting checks ReferenceEquals against the actual app
retained by the lease, verifies its own source belongs to that lease/root/catalog
and returns only the safe source. Binding is idempotent for that exact pair,
adds no registrations and does not consume/reset configuration or expose the
coordinator, private options or mutable evidence. Foreign-app/foreign-root and
substituted-source cases must fail before endpoint mapping.

Discovery registration must precede `EvaluateConfigurationAsync` or
`ValidateComposition`/compose. Existing proof snapshots must not be patched to
accommodate late registration. Registration/source resolution must not receive
HoardModuleOptions, secret handles, IConfiguration, argv or file readers.

## Composition and Publication

Within existing supervised ConfigureServices capture owner-added service
descriptors for explicit binding associations. Verify the exact effective
unkeyed single-service registration before build; a shadowed, removed or
wrong-owner descriptor cannot establish capability composition. Do not invoke
its implementation factory, inspect an instance or resolve the service.
Unsupported keyed/enumerable associations remain unavailable with safe reason.

Seal actual route owner/responsibility/method evidence using the existing
MapHoardModulesAsync route builder/validator. The two management routes are
ordinary host endpoints in that same conflict scan. Map them first; do not
bypass validation, add a custom matcher/data source or change route acceptance.
No capability can be usable until both binding ledgers are final.

Add an internal publication helper in the existing lifecycle coordinator. Under
its existing Gate, publish after every observable transition listed in the
[model](../data-model.md#published-lifecycle-state-and-read-envelope).
Keep projection/publication bounded and free of callbacks, I/O and serialization.
Readers take one volatile immutable reference and never acquire Gate or call
Snapshot/AssessReadinessAsync. All availability fields derive from that one
revision; no request subscribes or constructs a second coordinator.

Publication must not alter original lifecycle sequencing, callback supervision,
admission/resource ownership, shutdown deadlines or frozen stop results.
Readiness-assessment failure remains an authority result; discovery cannot
probe again or repair it. Readiness loss does not imply route removal/drain.
Terminal/late diagnostics can advance revision without reviving usability.

## Exposure and Authorization

Both endpoints require the configured host management-read policy and the shared
discovery exposure requirement. Absence of a named policy, invalid protection
options or missing required authentication services is a safe startup error.
No endpoint or static-file copy is AllowAnonymous or development-only bypass.

### Explicit local-loopback mode

- The host deliberately enables local anonymous management-read through its
  policy and asserts a direct, non-proxied local deployment. No cloud or
  external identity is required.
- Validate declared bindings and the actual server address feature: every
  effective address must be an explicit loopback IP or localhost, never
  wildcard, non-loopback, unknown or unsupported topology. A request cannot
  succeed while actual binding information is unavailable; startup rejects
  known-invalid bindings. The default production verifier supports Kestrel;
  other servers require separately implemented/tested verification.
- Require the direct transport peer to be loopback, not a substituted forwarded
  address; null/unknown peers fail. Reject any Forwarded/X-Forwarded-* input and
  any configured proxy/forwarded-header processing in this mode.
- A reverse proxy can deliberately omit forwarding headers and appear local.
  The host must not publish local anonymous management through such a proxy;
  process/network isolation and the explicit no-proxy deployment assertion are
  prerequisites, not something peer/Host headers can prove.

### Explicit secured-network mode

- Require an authenticated principal plus the host's management-read permission
  policy. A module's availability/identity scheme selection does not authorize
  the caller. F-04 supplies no production login, token issuer or header identity.
- Direct access requires HTTPS. A trusted-proxy deployment must explicitly
  configure trusted immediate peers/networks, forwarded-header processing and
  TLS termination; an untrusted or unverified proxy request fails closed.
  Do not clear trust lists or use unrestricted forwarded-header environment
  switches. The guard consumes validated host posture and raw peer information,
  not unvalidated request headers.
- A configuration assertion is not proof of external certificate handling or
  network isolation. Document that operator responsibility; TestServer cannot
  certify it. HTTP trusted-proxy hops are permitted only under that explicit
  trusted topology, never by checking X-Forwarded-Proto alone.

The raw connection information must be captured before host forwarded-header
rewrites. With discovery opt-in, the existing supervised build inserts its
Hosting raw-peer capture filter immediately after F-02's outer request-completion
boundary and before every pre-existing host startup filter/middleware. Do not
depend on the order in which a caller happened to register discovery.
The capture invokes no provider and does not bypass F-02 admission ownership.
Until protection/binding verification succeeds, both endpoints fail
closed with safe 503 rather than serving a public inventory. Authorization
denials disclose no module/configuration detail.

In-process fixtures use an internal test-only exposure verifier plus mock
authentication handlers to cover each policy branch. It must not be a public
production bypass. Separate mandatory adapter cases use private ephemeral
loopback Kestrel listeners to verify effective address acquisition, actual peer
capture before forwarding rewrites, HTTPS recognition and fail-closed behavior
before verification. Test certificates are generated in memory and pinned only
to that test client, never globally trusted or logged. All listeners/clients are
stopped/disposed within finite test budgets. No product/public listener is added
by the library, and this proof does not certify external proxies/certificates.

## Disclosure and Diagnostics

Public module/setting/operation identities must belong to frozen known metadata
and pass canonical length/shape limits. Any arbitrary external/unknown identifier
maps to a fixed placeholder, not an echoed input. Descriptions, publisher text,
constraints containing strings, defaults and examples require a separate
explicit host publication allowlist. Never copy the source record wholesale.
Secret-marked fields omit all value-like members; unapproved ordinary text is
suppressed with a safe explanatory category.

Existing safe lifecycle/configuration diagnostics are inputs to a closed
reason mapping, not returned directly. Unknown codes become safe categories.
Output failures include bounded reason, approved affected identity where known,
phase, corrective action and random correlation reference. No inner exception,
URL, private path, configured value, resolver target or raw provider message.

Owned telemetry uses bounded outcome/reason labels and route templates.
Correlation belongs in diagnostic events, not metric labels. Do not emit module
IDs/operation IDs as unbounded metric dimensions or dump request/response bodies.
The host must likewise avoid logging credentials/configuration; malicious
trusted in-process code is outside the disclosure mechanism's isolation claim.

## Failure, Bounds and Lifetime

Invalid static discovery metadata/options/associations fail before activation,
without invoking F-03 validators or touching disabled operational settings.
Unavailable source, incoherent identity, runtime unknowns, cancellation, deadline
or response-size overflow produce an explicit failed read, never a cached
successful fallback. Application encodes into a capped private buffer before
headers and discards it on failure; data/description responses are no-store.

No per-read background task, health callback, secret read, observer subscription,
service construction or retry. Cancellation is cooperative; trusted host auth/
middleware and transport must honor tokens. A response cannot retract bytes
already sent or preempt arbitrary code. Discovery does not dispose providers,
the coordinator or the root to enforce a request deadline.

Rollback is removal of opt-in/mapping and a compatible restart. There is no data
migration, runtime package removal, provider hot swap or infrastructure action.
