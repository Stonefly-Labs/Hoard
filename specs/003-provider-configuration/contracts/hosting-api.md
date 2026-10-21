# F-03 Hosting Configuration Library Contract

**Status**: Complete target for additive APIs in `Hoard.Hosting.Configuration`.
The [partial source MVP](../plan.md#source-resolution-mvp-implementation) supplies
metadata/inputs/safe reports and an always-failed evaluator; successful proofs,
configured compose/adapters, active checks, secret resolution and conversion
remain implementation obligations, not available behavior.
Abstractions, Core and Application receive no F-03 dependency or required member.

## Compatibility and Ownership Boundary

Keep F-01 `AddHoard`, `AddModule<TProvider>`, descriptors, registrations and
provider marker interfaces unchanged. Keep F-02 `AddModuleLifecycle`,
`IHoardModule`, `HoardStartupSelection`, validation and existing compose/build/
map/start/stop signatures unchanged. Old source and already compiled consumers
must work without a new required member, callback or configuration source.
Hosting's existing ASP.NET Core shared-framework requirement is unchanged.
No package/version publication occurs as part of planning or implementation.

New opt-in registrations live in Hosting. Metadata/artifact providers remain
Abstractions-only; host adapters own descriptions, checks and mapping to their
existing public APIs. Protocol/identity packages may use approved Hosting
contracts, never another concrete provider or management slice.

## Proposed Public Surface

| Surface | Agreement |
| --- | --- |
| `AddModuleConfiguration<TProvider>(HoardModuleConfiguration contract, HoardOptionValidator? validator = null)` on HoardBuilder | Record immutable metadata and an optional explicitly supplied delegate; do not construct a validator/provider or invoke a callback |
| `HoardModuleConfiguration` / `HoardOptionField` | Closed descriptive version/field/rule metadata; exactly one association per configurable provider registration |
| `HoardOptionValidator` | Async delegate `(HoardOptionCheckContext context, CancellationToken token) -> ValueTask<HoardOptionCheckResult>`; invoked for Public and Secrets phases separately |
| `HoardConfigurationInput` | Private bounded defaults document, optional explicit file, copied CLI args and injectable environment snapshot/read adapter for tests; source text/path never in ToString |
| `HoardConfigurationOptions` | Trusted host timing/size limits, TimeProvider injection; invalid finite budgets/limits fail before work |
| `EvaluateConfigurationAsync(input, platformVersions, lifecycleOptions, configurationOptions, cancellationToken)` on HoardBuilder | Returns `HoardConfigurationEvaluation`, either private validated proof plus safe report or explicit Failed/Cancelled/TimedOut report; never silently succeeds |
| `HoardConfigurationEvaluation : IAsyncDisposable` | Outcome, safe immutable report, safe live supervision snapshot, optional `HoardValidatedConfiguration`; no raw inputs/exceptions; disposing an unconsumed proof uses the same ownership gate |
| `HoardValidatedConfiguration : IAsyncDisposable` | Non-public construction; private fixed values and existing validated composition; single-use and exact builder/service/contract ownership |
| `ComposeHoardModulesAsync(HoardValidatedConfiguration configuration, CancellationToken token)` on HoardBuilder | Consume once, transfer owner inputs, then reuse the existing supervised F-02 composition sequence and lease |
| `IHoardConfiguredModule.ConfigureOptions(HoardModuleOptions options)` | New optional interface on lifecycle adapters only; called under F-02 supervision immediately before existing ConfigureServices |
| `HoardModuleOptions` / `HoardSecretValue` | Read-only typed getters for the one owner; explicit secret access, redacted display, no all-owner registry or source access |
| `PreviewConfigurationConversionAsync(...)` / `ApplyConfigurationConversionAsync(session, ...)` | Host/operator library operations; safe report/private single-use approval session; no product command, management endpoint or activation |

The input's injectable read adapter is a trusted host/test collaborator, not
a dynamic resolver/plugin mechanism. Production reference kinds remain env/file
only. Do not expose environment enumeration/whole config through module options.

## Metadata Association and Validation

An association identifies one already registered `TProvider`; duplicate/orphan
associations fail even if disabled. Each descriptor configuration key maps to
exactly one field after canonicalization; Required and SecretReference flags
must agree. No unknown extra fields or silently missing descriptor field.
Descriptors with zero configuration fields can use an implicit empty contract;
all others require an explicit contract for opt-in evaluation.
Metadata validation runs without creating providers/adapters/validator objects.

Fields describe type, requiredness, secret classification, length/range/allowed
ordinary values and a safe documented default/example. No secret default.
Cross-field rule IDs are finite declared safe identities. A validator returns
only field/rule identifiers and status, never an arbitrary message. Unknown
IDs, malformed results or failure payloads map to `InvalidCheckResult`.

Public-phase context exposes only this owner's effective ordinary fields and
whether its secret field has a syntactically valid reference, not reference
targets or resolved values. Secret-phase context exposes the same ordinary
values and explicitly resolved owner secret handles. Disabled modules get
neither callback. A validator is a trusted pure option check: no DI, provider
construction, file/network service I/O or external connection; necessary
reference reads are the separate host-owned bounded step.

Before secret resolution, inspect selected adapter types for configured-input
support. A nonempty configurable module must have an adapter implementing
`IHoardConfiguredModule`; fail `MissingConfigurationAdapter` without construction.
No-op zero-field modules need no new interface. Secret fields may not be delivered
through a non-secret accessor or serialized into the service collection.

## Sole Composition Gate and Bypass Prevention

Translate effective module/capability selections directly to F-02's
`HoardStartupSelection`; call existing `ValidateComposition` for the same
registered builder. Do not reimplement dependency/category/version/cardinality/
capability ordering or enable optional modules. Verify the additional identity
list matches enabled Identity modules; that list cannot change F-02's graph.
Map existing safe lifecycle diagnostics into the config phase/source context,
never attach raw options or exceptions.
F-02 may preserve a regex-valid supplied unknown module ID or dependency-path
element. F-03 must re-map every such identity against the known metadata set,
not forward the existing record directly. This includes errors from invalid
required capabilities and missing dependency targets, not just selections.

Evaluation snapshots services/contracts and all input values. A successful
proof retains the private existing composition; safe results do not expose it.
Configured compose atomically verifies exact builder, unchanged service and
configuration metadata snapshots, unused/non-disposed successful proof and no
pending work before transferring ownership. Cancellation wins if already
observed before dispatch. Repeated/concurrent consumption, foreign builder,
changed registry/contracts or mutation fails before adapter/provider construction.
Do not build an intermediate container.
Proof disposal and configured/legacy consumption share an atomic ownership
boundary: either the unconsumed proof releases its inputs, or exactly one
lifecycle lease owns them, never both. Race tests must include blocked delivery
and cancellation notification work, not just sequential duplicate calls.

When an enabled module has an opt-in configuration registration, calling legacy
compose with only `HoardValidatedComposition` must reject `ConfigurationRequired`
before any construction. Registration-only use and legacy F-02 compositions
without configuration opt-in retain their exact behavior. Manual trusted
application code can still deliberately bypass library APIs; this is an API
correctness rule, not a sandbox for malicious host code.

## Delivery Through F-02

Only successful configuration enters adapter construction. The configured
overload shares the existing internal implementation, ledger, activity tracker,
absolute lifecycle startup/stop deadlines and sole `HoardServiceComposition`
root owner. Add a supervised `ConfigureOptions` invocation in the existing
ComposingServices phase before ConfigureServices, not a second initializer,
root provider, hosted service or readiness authority.

An adapter stores its own immutable `HoardModuleOptions`, then maps only needed
typed values/secret handles into its operational registration. It must not
store a host resolver/input object or write secrets into descriptor metadata,
diagnostics or provider configuration files. Parameterless constructors stay
inert; ConfigureOptions/ConfigureServices may not connect/start workers.
Provider operational construction remains in the existing initialization path.

If delivery/configuration blocks or throws, F-02 records originating owner/
phase, poisons startup, retains pending inputs/resources and protects
prerequisites/root exactly as for existing callbacks. Later completion cannot
publish a host/ready result or trigger deferred provider/root disposal.
Owner options stay alive while relevant supervised work uses them; never
dispose all secret inputs just because a bounded wait returned.

## Safe Results and Failure Categories

Reports are closed host-created records: source kind, safe registered setting/
module identity or ordinal, phase, status, rule, corrective action and random
correlation ID. Cap diagnostics at 100 with omitted count; cap every identity
and array before formatting. Unsafe values that happen to match a safe-name
regex are still not reflected unless from known metadata; an unknown supplied
key gets `unknown-setting`, not its text.

Rule families include SourceUnavailable/InvalidSource/DuplicateSetting/
UnknownSetting/UnsupportedVersion/InvalidSelection/CompositionRejected/
MissingConfigurationContract/InvalidConfigurationContract/
MissingConfigurationAdapter/MissingOption/InvalidOption/InvalidSecretReference/
UnsupportedSecretKind/SecretUnavailable/InvalidCheckResult/CheckFailure/
Cancelled/Timeout/CancellationFailure/LateCheckFailure/StaleConfiguration/
ConfigurationRequired/ConversionRejected/PublicationFailed.
Host templates supply corrective actions; provider rule IDs select reviewed
templates, never free-form messages. Do not retain raw inner exceptions in
public errors, failure objects, log calls or emitted telemetry.

Only evaluation-owned safe events are emitted. Existing host logging must not
dump IConfiguration/argv/environment/private objects; fixture capture covers
configured-host normal results/logs/telemetry. Arbitrary provider code is trusted
and cannot be prevented from logging directly; the contract prohibits it and
tests representative compliant/faulting fixtures, not process isolation.
Metric dimensions use closed phase/category/source labels; correlation belongs
in diagnostic events, not high-cardinality metric labels.

## Pending Work, Disposal and Conversion

Follow the [model's retention rules](../data-model.md#concurrency-budgets-and-resource-ownership).
Use the existing F-02 supervision pattern as prior art for full-callback
dispatch, separate cancellation notification, originating-phase fault recording
and frozen results; do not couple pre-composition tasks to a nonexistent root.
Serial evaluation cannot dispatch another resolver after a pending timeout.
Explicit disposal of evaluation/proof is bounded; it reports retained pending
resources rather than disposing in-use objects or waiting indefinitely.

Conversion operates on explicit file/default documents only; it neither
reads ambient overrides nor constructs adapters/providers. Preview validates
public proposal semantics; approval applies the same evaluator fully, without
compose. The session pins original bytes, proposal, mapping/contract/builder
identity and approved fresh destination. Re-preview changed content; never
approve one report and publish another. Resolver errors cannot leak into
conversion errors or publish a replacement. Full startup validation still
runs later, because secret targets can change after apply.

## Compatibility Proof Obligations

Retain F-01 compiled registration binary, new source consumers, public graph
scans and framework propagation checks. Also retain a pre-F-03 F-02 lifecycle
consumer binary, run it with new local Hosting packages without recompilation,
and build an equivalent new-source consumer. Configured package-only baseline
and custom examples must use no source ProjectReference escape or concrete
cross-provider reference. Abstractions/Core public API and package dependencies
must remain unchanged; approved Hosting additions need actual packed graph
inspection. Planning does not certify any of these proofs.
In addition, build and retain an option-bearing metadata/artifact fixture
against pre-F-03 Abstractions, then use that unchanged provider binary with a
new configured host adapter for ordinary and secret options. Existing fixtures
with `Configuration = []` alone cannot prove this boundary.
