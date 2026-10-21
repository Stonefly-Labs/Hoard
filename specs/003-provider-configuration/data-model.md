# F-03 Configuration Model

**Status**: Implemented Hosting model, not storage entities. See the
[complete fixture evidence](plan.md#complete-implementation) and historical
[source MVP](plan.md#source-resolution-mvp-implementation), [format](contracts/configuration-format.md)
and [library contract](contracts/hosting-api.md).

## Entities and Relationships

| Entity | Fields / relationships | Invariants |
| --- | --- | --- |
| ConfigurationSource | kind Defaults/File/Environment/CommandLine, bounded ordered assignments, private origin | One of each kind; one explicit file; private path/text never reported |
| SettingIdentity | normalized root/module/option path, optional registered owner | ASCII key segments; metadata-bijective identity; values are not normalized |
| SourceAssignment | canonical identity, typed token, occurrence, source kind | Unique in that source, even if later overridden; structural shape checked before merging |
| ModuleConfigurationContract | provider type association, current/supported option versions, immutable fields/rule IDs | Exactly one association per configurable registered provider; no factories/construction/I/O |
| OptionField | key, type, required, secret flag, public constraints, optional documented default | Bijective with descriptor keys; defaults only apply when explicitly present in defaults source |
| EffectiveConfiguration | frozen selections/options/provenance, independent document versions, registry identity | No reload or mutable source references; private values separated from safe view |
| ProviderSelection | enabled IDs, metadata/artifact IDs, identity IDs, capability requirements | Identity set agrees exactly with enabled Identity category; F-02 validates remaining graph |
| SecretReference | kind Env/File, private target, owner/setting | Closed grammar, no expression; absent optional secret differs from empty literal/reference |
| ResolvedOwnerOptions | fixed typed ordinary values and secret handles for one owner | No whole-host access; no reread; no public automatic serialization or value-bearing ToString |
| ConfigurationEvaluation | operation ID, terminal outcome, safe report, live safe supervision snapshot | Success only after all checks; failure has no composition proof; frozen returned outcome |
| ValidatedConfiguration | private composition, exact builder/service/contract snapshot, fixed owner inputs, single-use flag | Not publicly constructible; consumption atomic; stale/failed/disposed proof cannot activate |
| ConfigurationDiagnostic | bounded safe identity/category/source/phase/rule/declared OptionRule/action/correlation | OptionRule must match validated owner metadata; source follows the effective field; host-owned codes/templates, no raw collaborator/source/error strings |
| PendingConfigurationActivity | owner/setting/source/phase/task, held input/CTS/stream lease, safe observation | Origin retained through notification/late faults; outlives bounded wait when necessary, never represented as terminated/released |
| ConversionSession | private original/proposal bytes and digests, registry/mapping identity, opaque session ID, safe changes | Preview does not resolve secrets; no public digest/locator; single approved apply |
| ConversionPublication | new destination, private same-directory staging handle, terminal publication outcome | Never overwrite source/destination; complete file or no final file; original retained |

## Option Representation and Structural Validation

Ordinary option values are string, Boolean, Int64 or an address string.
Secret values are reference objects only. Types, key counts and reference
grammar are structural obligations in every supplied source. Public range,
requiredness, allowed-value, absolute-address semantic and cross-setting
constraints apply only to effective enabled values. Credential-bearing
address components are rejected structurally in every occurrence.

No nested arbitrary provider objects, null, numeric coercion, string-to-Boolean
conversion or implicit list indexing. The only module option object has
`optionsversion` and `options`; only registered known option fields are legal.
Missing values are represented as absent, never empty defaults.
Representable but invalid lower-priority values may be overridden; malformed
syntax/shape, unknown names, duplicates and unsafe secret representation may not.

Provider IDs follow the exact existing F-02 lowercase ID policy.
Canonical setting-key comparison is ASCII ordinal case-insensitive; metadata
keys that collide after normalization make the configuration association
invalid. This does not change F-01 declaration acceptance outside opt-in use.
Descriptions/default examples are reviewed author metadata, not error text.

The contract's documented default is informative until the composing
distribution includes it in its Defaults source. Do not materialize optional
values or recover invalid effective values from metadata after merging.

## Evaluation State Machine

```text
Created
  -> ReadingSources
  -> StructuralValidation
  -> Merging
  -> CompositionValidation (existing F-02 gate)
  -> PublicOptionValidation (enabled only)
  -> SecretResolution (enabled owner fields only)
  -> SecretOptionValidation (enabled only)
  -> Validated -> ConsumedByLifecycle

Any nonterminal stage -> Failed | Cancelled | TimedOut
Validated -> Disposed | RejectedStale
```

Failure/timeout/cancellation closes dispatch under the evaluator gate before
returning. Later task success cannot enter a next stage or create a proof.
Returned outcome/report are immutable. A separate safe observation snapshot
may append bounded eventual-failure diagnostics or update pending counts.
It cannot revise the returned outcome or silently retry. No F-02 lifecycle
exists before successful configured compose, so no provider/root cleanup is
delegated to this evaluator.

Each active module follows public validation before any secret work begins
for any module. Secret-dependent validation runs only after required references
for selected owners succeed. Stop on failure; do not continue resolving
unrelated secret fields to collect additional errors.

## Concurrency, Budgets and Resource Ownership

- The operation owns one monotonic deadline from entry, including input reads,
  metadata gate and report construction. Defaults: 30 seconds outer, five
  seconds per dispatch capped by remaining time. Serial dispatch prevents a
  failed operation from accumulating multiple abandoned checks.
- Bound input size while reading, not after ReadToEnd. Copy injected in-memory
  source data before use. Include parser/metadata work in supervision and
  check cancellation/deadlines between bounded iterations.
- A supervised task records activity before dispatch, then executes the entire
  callback, including any synchronous prefix. Wait completion does not release
  the underlying activity. A scheduling starvation limit is not real-time OS
  preemption; tests distinguish deadline math from scheduler tolerance.
- Notification of collaborator cancellation is tracked work too. Caller-token
  callbacks never invoke collaborator cancellation inline. Each task observes
  its own exceptions before releasing its lease; notification failures map to
  safe additional errors in the originating phase.
- After bounded failure, an in-use input buffer, secret material, stream or
  cancellation source remains owned by the still-running task/notification.
  Task-local finally blocks release their resources only after actual use
  ends; there is no deferred provider/root disposal, activation or result
  publication. A permanently blocked trusted callback can require terminating
  the process; bounded coordination cannot forcibly clean it up.
- An unused successful proof owns its sensitive inputs until explicit disposal.
  Configured compose transfers them once to the existing F-02 lease before
  adapter construction; rejection transfers nothing. The lease retains owner
  inputs during pending F-02 callbacks and releases them only when safe.
  Do not introduce a second DI/root-disposal owner.
- Public strings and secret material are immutable inputs. A secret handle's
  string access is explicit for the selected adapter; ToString/debug displays
  are redacted. Clearing owned buffers is best effort, not managed-memory
  zeroization or protection from trusted process code.

## Conversion State Machine

```text
ExplicitSyntheticInput
  -> ParseAndMap
  -> ValidatePublicProposal
  -> Previewed
  -> ExplicitApproval
  -> RecheckOriginalAndContext
  -> FullValidationWithoutActivation
  -> PrivateStaging
  -> FlushAndClose
  -> NoClobberPublish
  -> PublishedNewFile
```

Reject missing/unknown versions, unmapped keys, unverifiable preservation,
changed original bytes/mapping/registry, an existing destination or invalid
proposal. Error/cancellation before publication yields no final destination;
crash/interruption may leave an identified private staging file, never a
partially written final file. On success the new file is complete and startup
still must validate it anew. A cancellation concurrent with the atomic publish
point reports the actual publication outcome, not a false "not published".
If dispatched filesystem publication has not returned by a bounded wait, return
explicit `PublicationPending` and retain its task/staging ownership. A safe
observation may later report the actual complete-file outcome, never rewrite
the returned outcome or claim definite rollback while commit is still running.
Cancellation before dispatch prevents publication; cancellation after dispatch
is not proof that an OS file operation stopped.

The original is never edited, moved, removed or used as an output destination.
Input and existing destination aliases/hardlinks/symlinks are not overwritten;
new output is no-clobber. Owner-restricted directories are a precondition, not
an adversarial filesystem sandbox. No generic cloud/network-filesystem,
hardware power-loss, source-provider data-reversal or cross-process transaction
is implied.

## Persisted Versus Safe Representations

Private source/proposal bytes may contain reference locators and ordinary
values, never resolved credentials. Safe reports expose only registered safe
setting/module identity (or a host-generated ordinal), winning source kind,
phase, validation status/rule/action and correlation. Changes use categories
Added/Removed/Changed/ReferenceChanged/SelectionChanged/VersionChanged;
no old/new raw values, locators, content hashes or provider exception text.
Neither private proofs nor options are DTOs for F-04 discovery.
