# F-03 Operator Configuration Contract

**Status**: Implemented version 1 library grammar and explicitly synthetic
conversion, backed by [fixture evidence](../plan.md#complete-implementation).
There is no operator executable or support for illustrative product YAML.
Examples contain fixture IDs and invented reference targets, not credentials.

## Documents and Sources

Only these sources affect Hoard module configuration, low to high precedence:
explicit distribution Defaults document, one explicitly selected File document,
the optional `HOARD_CONFIG` Environment JSON overlay, and CommandLine
assignments. No automatic appsettings, user-secrets, current-directory search,
UI state, reload watcher or remembered successful configuration.

A defaults document always declares integer `configurationversion: 1`.
Each supplied file independently requires that exact version. A file is
optional only when not requested; `--hoard-file=<path>` selects exactly one,
and repeated/unreadable/empty file arguments fail. The host may instead supply
the explicit path programmatically, but may not combine both selectors.
Paths are private inputs and never repeated in normal errors.

Environment input is one JSON object in `HOARD_CONFIG`, using the file body's
keys except `configurationversion`, which is forbidden in overlays. Enumerate
case-equivalent environment names before reading: both `HOARD_CONFIG` and
`hoard_config` on a case-sensitive OS are a same-source duplicate, not an
arbitrary winner. Other variables are not module settings; selected
environment secret targets are read only during secret resolution.
An absent variable means no overlay; an explicitly empty variable is invalid
JSON. No generic `__` translation or process-wide IConfiguration binding.

CLI assignments are one argument each: `--hoard:<path>=<JSON-value>`.
Path segments use `:`; permitted leaves are the root selections and
`modules:<module-id>:optionsversion` / `modules:<module-id>:options:<option-key>`.
The RHS is a complete JSON value, even for strings; shell quoting only protects
the argument and is not interpreted by Hoard. Unknown `--hoard...` arguments,
missing `=`, duplicate canonical paths or assignments to intermediate objects
fail. Unrelated host arguments belong to the host, never implicitly to Hoard.
The host must extract Hoard arguments before constructing a generic host with
unfiltered args and must not log raw args on parse failure.

```text
--hoard:enabledmodules=["fixture.metadata","fixture.artifact.one","fixture.protocol.one"]
--hoard:artifactmodule="fixture.artifact.one"
--hoard:modules:fixture.protocol.one:options:enabledcache=true
```

This is argument syntax, not a shell command or a runnable application.
Never put a secret literal on the command line.

## Current File Shape

```json
{
  "configurationversion": 1,
  "enabledmodules": [
    "fixture.metadata",
    "fixture.artifact.one",
    "fixture.protocol.one"
  ],
  "metadatamodule": "fixture.metadata",
  "artifactmodule": "fixture.artifact.one",
  "identitymodules": [],
  "requiredcapabilities": [],
  "modules": {
    "fixture.protocol.one": {
      "optionsversion": 1,
      "options": {
        "enabledcache": true
      }
    }
  }
}
```

This document requires corresponding registered fixture contracts; arbitrary
example fields are not accepted for modules without those declarations.
An absent optional selection/options key may inherit Defaults. Required
effective selections cannot be absent/empty. An explicit `[]` is an empty
selection, never omission. Exactly one metadata/artifact ID must agree with
enabled modules and category. `identitymodules` must equal the set of enabled
Identity-category modules, including an explicit empty set when none.
Multiple protocols/identities are valid. No auto-enablement.

`requiredcapabilities` is a whole replaced array of objects with exactly
`module`, `id`, `range`, `allowprerelease` fields (string/string/string/Boolean).
Translate them to F-02's existing required-capability records without changing
its version/prerelease policy. Their semantic ranges/targets are evaluated only
on the effective selection by the existing gate.

Only listed root keys and registered `modules`/option keys exist. No server
binding, public URL, registry, permission, data migration or UI-setting keys
are introduced. Unknown product-sketch fields fail rather than claiming
security/listener behavior that F-03 does not implement.

## Canonical Names, Duplicates and Merge

Keys use ASCII letters/digits with single internal `.`/`-` separators, start/end
alphanumeric, maximum 128 characters; structural words are as listed above.
ASCII letters normalize to lowercase for key identity. Module identifiers
used as selection values must already satisfy F-02's exact lowercase ID policy;
never lower-case arbitrary values to change composition acceptance.
Descriptor option keys are mapped bijectively to their normalized form;
an unsafe/unmappable/colliding descriptor key fails opt-in contract association.

Decode JSON property escapes before checking identity. Reject repeated object
properties, case-equivalent keys, repeated selection IDs and duplicate
capability identities even if their values agree. CLI paths use the same
canonical identities. Whitespace around JSON tokens is allowed; whitespace
inside names is not normalized. Nulls, comments and trailing commas fail.

Parse each source separately. Structural checks apply to every occurrence,
including overridden/disabled ones: valid JSON/shape, known keys, canonical
uniqueness, primitive type, valid reference object syntax and no credential
address representation. Scalar range/allowed-value, requiredness, active option
versions and cross-setting semantics apply only to effective enabled values.

Whole `enabledmodules`, `identitymodules` and `requiredcapabilities` arrays
replace the lower-priority array; metadata/artifact choices replace as scalar
values. `modules` objects merge by owner and individual option field;
`optionsversion` is a separate leaf. A secret reference object is one atomic
option value, not a mergeable kind/target object. Preserve winning source kind
per effective leaf/whole selection. Never apply a schema default after merge.

## Option Descriptions and Effective Rules

Each configurable registration provides field types, required/secret flags,
finite string/integer limits, any enumerated ordinary values, address rules,
safe descriptive defaults/examples, allowed option version and public
cross-setting rule IDs. Current active option version is integer 1; an active
module with a nonempty option contract must have an effective optionsversion.
Disabled modules may omit it or carry an unsupported but structurally integer
version; operational compatibility/requiredness is not checked for them.

String/Boolean/Int64/address are the only ordinary field types. No coercion
from JSON strings to numbers/Boolean, arbitrary nested objects or extra fields.
Ranges and cross-setting rules run only on effective enabled fields. The
address type permits absolute HTTP(S) URLs only after effective validation,
and structurally rejects user-info, query and fragment in every supplied
occurrence to prevent credential-bearing representations. Authors must mark
credential fields as secrets, not strings; this is not an arbitrary-secret
detector or a general upstream SSRF policy.

## Secret References

A secret field accepts exactly a reference object:

```json
{"kind": "env", "target": "HOARD_FIXTURE_CREDENTIAL"}
```

```json
{"kind": "file", "target": "/run/hoard-fixture-secrets/credential"}
```

`kind` is exactly `env` or `file`; no fallback chain, scheme loading,
interpolation, shell execution, recursion or quoting language. `target` is a
private string, never an ordinary diagnostic value. Environment names match
`[A-Za-z_][A-Za-z0-9_]{0,127}` and are looked up with OS semantics, without
case conversion. File targets are absolute local paths, not URLs; no `~`,
environment expansion or config-relative lookup. A string secret literal,
unknown kind, missing/extra field or invalid target shape fails even when
overridden or disabled. A syntactically valid nonexistent disabled target is
not opened.

Resolve only active fields after all composition/public option checks pass.
Missing/zero-length/whitespace-only/denied/too-large/unreadable targets fail
without trying another source. Mounted files contain strict UTF-8 text without
BOM/NUL, at most 64 KiB; remove at most one terminal LF and its preceding CR,
not arbitrary whitespace. Environment values retain their exact nonempty
text. Files must be local regular targets, not directory/device/pipe inputs;
deployment-owned symlinks to regular mounted files are allowed. Open once and
bound reads. Tests must prove supported-platform regular-file checks and
bounded behavior; same-user concurrent filesystem attacks are not sandboxed.

Each active owner/field receives one frozen resolved value. Reusing a reference
explicitly for two owners resolves each field independently; no cross-source
atomic rotation or cross-owner options access. Source/secret changes do not
affect the running lifecycle; restart re-resolves everything. Managed values
are sensitive in process memory, not an isolation boundary.

## Validation, Diagnostics and Budgets

Order: source/structure -> merge -> existing composition gate and contract
association -> all active ordinary rules -> active secret resolution ->
secret-dependent checks -> private success proof -> F-02 composition/activation.
No provider/adapter construction or provider service I/O before success.
Disabled modules get no operational callbacks, secret reads, workers/routes
or connection attempts. Failure never selects another store/anonymous mode.

Default configuration coordination is 30 seconds outer/five seconds per
dispatched operation, capped by remaining outer time. See the
[model](../data-model.md#concurrency-budgets-and-resource-ownership) for pending
inputs and cancellation notification. F-02's later startup/stop deadlines
remain separate, existing lifecycle budgets, not multiplied config timeouts.

Safe output contains registered safe setting/module identity or generated
ordinal, source kind, phase/category, rule, corrective action and correlation.
No values, raw versions/names, file paths, reference targets, hashes of secrets,
parser text, arbitrary validator result messages or exception/inner exception.
Reports include at most 100 diagnostics plus omitted count; normal telemetry
uses bounded category labels, never per-secret or per-correlation metric labels.
For a declared option-check rejection, `Rule` remains `CheckFailure` and
`OptionRule` identifies the validated declared rule, for example `paired`;
Setting and Source identify the effective field, not its discarded lower source.
Unknown/malformed callback identities become InvalidCheckResult without reflection.
Active option-version errors name `modules:<owner>:optionsversion`.
Secret failure/timeout/cancellation and eventual notification/check faults retain
their original registered field/source without exposing the target. Returned
reports never change; live Supervision can append bounded eventual diagnostics.

## Explicit Conversion and Recovery

There is no supported released older format. Startup accepts version 1 only.
For mechanism acceptance, explicit converter mode supports synthetic
`configurationversion: "fixture-v0"` with these exact renamed root fields:

| Synthetic root | Version 1 root |
| --- | --- |
| `enabled` | `enabledmodules` |
| `metadata` | `metadatamodule` |
| `artifact` | `artifactmodule` |
| `identities` | `identitymodules` |
| `capabilities` | `requiredcapabilities` |
| `providers` | `modules` |

All six selection/provider fields are required in the synthetic input;
provider subobjects retain `optionsversion`/`options`. Copy every explicit
selection, option and secret-reference object exactly in meaning, changing
only listed root names and the version. Unknown/unmappable fields, unsupported
option versions, omitted selections or proposed provider/access changes fail.
There is no converter for unversioned/YAML/other invented formats.

Preview performs structure, composition and non-secret option validation
without reading secrets; its safe change list contains categories/identities,
never old/new values or reference targets. Return an opaque private conversion
session, not a public raw proposal or content hash.
Explicit apply consumes that session once after verifying unchanged original
bytes, registered contracts/mapping, proposed content and approved destination.
It repeats full validation including required secret resolution/checks without
provider construction, then serializes the original references, never resolved
values. No env/CLI overlays are applied during conversion; startup overlays
remain a separately documented operator obligation.

Write an exclusive owner-private staging file in the new destination's
owner-restricted directory. Flush/close and publish no-clobber on the same
filesystem; reject an existing destination, including aliases to the source.
Never overwrite or delete the original. Interruptions leave either no final
file or a complete valid final file; private abandoned staging is identified by
a safe category and cleaned only via an explicit documented local procedure.
Do not log its path. Supported local platform publication proof is mandatory;
no power-loss/hardware durability, hostile-directory or network-share guarantee.
When a bounded wait ends after publication was dispatched but before it
returns, report `PublicationPending`, not success or a definite "not published".
Retain and observe the operation safely; the eventual new file is absent or
complete, never partial. See the [conversion state model](../data-model.md#conversion-state-machine).

Operators retain the original/reference set and explicitly point the next start
at the new file. If it fails, stop, restore a coherent compatible distribution,
configuration and references, and restart; no automatic previous-config reuse.
Provider-owned data/schema compatibility and backups are separate prerequisites.
Configuration restoration cannot reverse those data changes.
