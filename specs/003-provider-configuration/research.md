# F-03 Research and Decisions

**Status**: Planning decisions, not implemented behavior.
**Date**: 2026-10-20. Input: [specification](spec.md), merged F-01/F-02 APIs,
constitution and a bounded public-documentation research agent.

## R1: Strict Sources Instead of Generic Host Binding

**Decision**: Use System.Text.Json to parse defaults, one explicit file and an
optional `HOARD_CONFIG` JSON overlay. Parse `--hoard:<path>=<JSON>` assignments
as a separate source. Preserve occurrences, canonical names, explicit empty
values, types and source kind before merging. Replace selection arrays whole;
merge provider option fields by canonical key. Do not read `IConfiguration`,
appsettings/environment-specific files, User Secrets or UI-managed state.

**Rationale**: The default host chain permits extra sources and flattened
indexed arrays do not carry the whole-selection provenance required by FR-003.
Repeated binder collection operations can extend collections. Once flattened,
overridden source errors and duplicates cannot reliably be recovered. One JSON
environment overlay is portable even for dotted/hyphenated module IDs and
avoids a second delimiter/escaping grammar. It can supply many option overrides
without relying on OS environment name punctuation.

**Alternatives considered**: Generic host providers plus Bind once still lose
source boundaries/whole-array intent; repeated Bind compounds merge surprises.
YAML adds a dependency and aliases/type semantics without an MVP need.
Per-key environment variables require a reversible module-ID encoding or an
ambiguous underscore translation. A UI store is unrequested hidden state.

Sources:
- [Configuration providers](https://learn.microsoft.com/en-us/dotnet/core/extensions/configuration-providers)
- [Dictionary collection binding changes](https://learn.microsoft.com/en-us/dotnet/core/compatibility/extensions/7.0/config-bind-dictionary)
- [.NET 10 null binding](https://learn.microsoft.com/en-us/dotnet/core/compatibility/extensions/10.0/configuration-null-values-preserved)

The replacement algorithm is Hoard's explicit decision, not a claim that
Microsoft prescribes this grammar.

## R2: Occurrence-Aware Parsing and Closed Option Types

**Decision**: Enumerate JSON properties/arrays with bounded parsing and track
canonical names per object and flattened assignment per source. Normalize ASCII
key segments case-insensitively; reject aliases/collisions after decoding JSON
property escapes. Do not rely solely on exact-name duplicate detection.
Closed ordinary option types are string, Boolean, signed 64-bit integer and
absolute HTTP(S) address; secrets have a reference object. No arbitrary
polymorphic deserialization or binder coercion.

**Rationale**: .NET 10 offers duplicate-property rejection, but `Name` and
`name` still need Hoard's canonical collision test. Keeping raw JSON until
structural validation distinguishes wrong shape from discarded semantic
values. An out-of-range lower-priority integer is discarded only if still a
representable integer; an unknown key or malformed reference never is.

**Alternatives considered**: Last-value JSON lookup loses duplicates.
Generated general JSON Schema and reflection-based options introduce machinery
not required for the bounded contract; arbitrary objects weaken secret and
ownership classification.

Sources:
- [.NET 10 JSON changes](https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-10/libraries#serialization)
- [Utf8JsonReader](https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/use-utf8jsonreader)

## R3: Host-Owned Metadata and Additive Adapter Delivery

**Decision**: Put new option contracts, validators and optional configured-adapter
interface in `Hoard.Hosting.Configuration`. Associate contracts with already
registered provider types; do not extend `ModuleDescriptor`,
`ConfigurationRequirement`, family markers or `IHoardModule` with required
members. Enrich the existing descriptor keys by a one-to-one canonical mapping;
Required/SecretReference classifications must agree.

**Rationale**: Existing descriptor fields describe key/description/required/secret
only. Metadata/artifact providers have no permitted Hosting edge. Their host-side
adapters already exist in F-02 and can own configuration mapping without a
provider recompile. The configured interface supplies a frozen owner-only
bag before existing ConfigureServices under F-02 supervision.

**Alternatives considered**: Required Abstractions members break old binaries.
Injecting the whole configuration/secret registry through DI grants excessive
accidental access. A new options assembly or generic factory/DI extension
framework is unnecessary. Trusted in-process adapters remain unsandboxed.

Repository evidence: existing
[`ConfigurationRequirement`](../../src/Hoard.Abstractions/Modules/ConfigurationRequirement.cs),
[`IHoardModule`](../../src/Hoard.Hosting/Lifecycle/IHoardModule.cs),
[`ComposeHoardModulesAsync`](../../src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs)
and [F-02 public contract](../002-module-lifecycle/contracts/public-api.md).

## R4: One Existing Composition Authority

**Decision**: Translate effective selection to existing `HoardStartupSelection`
and call `ValidateComposition` before active checks/secrets. A private successful
configuration proof carries that result and exact builder/service snapshot.
Configured compose consumes it once; stale mutation fails before construction.
For enabled modules with configuration registrations, the legacy compose path
cannot omit the configuration proof. Old F-01/F-02 callers without that opt-in
remain unchanged.

**Rationale**: The existing gate already handles declarations, categories,
required/optional dependencies, versions, capabilities, cardinality and ordering.
Only identity-list agreement and configuration contract association belong in
the new boundary. Disabled declarations retain F-02's distinction between
structural validity and active compatibility.

**Alternatives considered**: A second graph validator risks divergent optional
dependency rules. Returning the bare validated composition publicly from the
new evaluation would permit skipping required option/secret validation.

Repository evidence:
[`ValidateComposition`](../../src/Hoard.Hosting/Composition/HoardCompositionExtensions.cs),
[`HoardValidatedComposition`](../../src/Hoard.Hosting/Composition/HoardValidatedComposition.cs)
and [F-01 compatibility policy](../001-provider-contracts/contracts/compatibility.md).

## R5: Bounded Waiting Is Not Termination

**Decision**: Supervise the entire evaluation under a monotonic absolute
30-second default budget; cap each read/check/resolution at five seconds and
remaining time. Dispatch even the synchronous prefix of trusted checks off the
coordinator. Close admission before signalling cancellation. Track the original
task and cancellation notification work; a timed-out wait never releases its
inputs or authorizes activation.

**Rationale**: Task.WaitAsync limits a wait, not underlying execution.
Cancellation callbacks can block synchronously or throw; direct Cancel or
disposing a registration/CTS while arbitrary callbacks run can defeat a finite
return. Caller-token registrations only mark terminal state and schedule
supervised notification, never invoke provider callbacks inline. Catch at the
external-code boundary to map failure codes, not to continue successfully.

**Alternatives considered**: Passing linked caller tokens directly to trusted
checks exposes caller cancellation to blocking callbacks. Task.Run alone
without tracking still abandons resources/faults. Thread abort, forced cleanup
or a sandbox claim is invalid. A second lifecycle coordinator is unnecessary:
pre-composition tasks have only private configuration resources.

Sources:
- [Cancel synchronous callbacks](https://learn.microsoft.com/en-us/dotnet/api/system.threading.cancellationtokensource.cancel)
- [Register on an already-cancelled token](https://learn.microsoft.com/en-us/dotnet/api/system.threading.cancellationtoken.register)
- [CancelAsync](https://learn.microsoft.com/en-us/dotnet/api/system.threading.cancellationtokensource.cancelasync)
- [Task.WaitAsync](https://learn.microsoft.com/en-us/dotnet/api/system.threading.tasks.task.waitasync)
- [Cancellation of non-cancelable operations](https://devblogs.microsoft.com/dotnet/how-do-i-cancel-non-cancelable-async-operations/)

CancelAsync is not itself a finite-completion guarantee. Actual supervisor
dispatch, notification, retention and late-fault races require focused proof.

## R6: Explicit Local References and Closed Safe Output

**Decision**: Accept only environment/file reference objects in secret fields.
Resolve once per active owner/setting; no interpolation or recursive expansion.
Use a safe report with identifiers from registered/validated metadata, source
kind and closed rule/action codes, never arbitrary value or error formatting.
Apply safe mapping to every phase, including parser keys, version errors,
callback output, file errors, cancellation and conversion.

**Rationale**: Redacting selected substrings from exception text is incomplete.
A URI's user-info/query/fragment can contain credentials, so the address type
rejects all of them, even in discarded or disabled inputs. Mounted-file
references allow deployment-owned symlinks for rotation, reading one opened
target per evaluation; no cross-secret atomic rotation is claimed.

**Alternatives considered**: Inline credentials and arbitrary URI interpolation
make diagnostics unsafe. A cloud secret service adds personal-use dependencies.
Secret strings are not process-memory isolation: immutable managed strings
cannot be reliably zeroized, and trusted code can still read process resources.

## R7: Original-Preserving, Explicit Offline Conversion

**Decision**: Current startup format is integer version 1. A separate converter
accepts one fully described `fixture-v0` synthetic input only on explicit request.
Preview is secret-free and non-activating; apply requires its opaque approval
session and unchanged input/mapping context, then repeats full configuration
validation. Serialize references, never resolved values, into private staging
beside a new destination; flush/close and no-clobber publish. Never rewrite
the source or overwrite an existing destination.

**Rationale**: No released older format exists. A synthetic mapping proves the
mechanism without promising compatibility with illustrative product YAML.
Fresh output plus retained source is simpler and safer than in-place rewrite
and backup renaming. Same-directory staging avoids cross-volume copy fallback.
Unix private modes and an owner-restricted destination directory/Windows ACL
precondition protect locators; FileShare.None is not a permissions substitute.

**Alternatives considered**: Startup auto-conversion, best-effort key guessing,
overwrite=true and cross-directory temporary files risk silent changes or
partial visibility. Generic File.Move documentation alone does not establish
all OS/filesystem crash guarantees; platform publication tests gate support.
No universal power-loss, directory-fsync, hostile-directory or network-share
durability is claimed.

Sources:
- [File.Move and cross-volume behavior](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.move)
- [FileStream.Flush](https://learn.microsoft.com/en-us/dotnet/api/system.io.filestream.flush)
- [FileStreamOptions.UnixCreateMode](https://learn.microsoft.com/en-us/dotnet/api/system.io.filestreamoptions.unixcreatemode)
- [FileShare](https://learn.microsoft.com/en-us/dotnet/api/system.io.fileshare)
- [Linux rename semantics](https://man7.org/linux/man-pages/man2/rename.2.html)

## Resolution and Evidence Limits

All planning unknowns are resolved into explicit design choices; none requires
a new product decision. Public research is not execution evidence. The exact
single-use integration, callback ownership, redaction, filesystem publication
and old-binary compatibility must be proved during implementation.
No agent inspected private source externally, edited files or queried Azure.
