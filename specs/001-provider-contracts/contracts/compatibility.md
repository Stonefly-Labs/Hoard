# F-01 Compatibility Policy

**Status**: Planned public contract policy and acceptance examples. F-01 has
no production runtime compatibility evaluator; enforcement belongs to F-03.
There is no implication of current published packages or supported deployments.

## Three Separate Version Axes

- **Abstractions version** identifies the provider-neutral public API and
  behavioral agreement consumed by provider authors.
- **Host version** identifies the platform composition/runtime release a
  provider claims to support, not an arbitrary custom host's assembly version.
- **Module version** identifies the independently released provider package.
  Module dependencies constrain this version, not the provider's host range.

Use normalized `major.minor.patch` with optional SemVer prerelease/build
metadata, not assembly revision numbers or floating package versions.
The initial local foundation packages use `0.1.0`; no release is authorized.
Package metadata/docs must identify the contract version they implement.

## Range and Prerelease Interpretation

Use NuGet interval notation, restricted to exact `[1.2.3]` or bounded intervals
such as `[1.2.3,2.0.0)`, with explicit three-part endpoints. Both inclusive and
exclusive bounds are supported. Reject missing/empty ranges, bare minima,
wildcards/floating ranges, reversed/empty intervals, and unbounded intervals.
An exact single version is an inclusive one-element interval.

A candidate is supported only if its normalized version falls within the
interval **and** it passes the axis-specific prerelease gate. Stable host/
abstractions versions have separate ranges; each must pass. Prerelease
host/abstractions candidates require the corresponding explicit boolean flag.
Prerelease dependency candidates require `ModuleDependency.AllowPrerelease`.
Range text containing `-rc` does not implicitly set any flag.

Compare using NuGet's semantic precedence: numeric components numerically,
prerelease labels case-insensitively, and no precedence distinction from build
metadata. A prerelease precedes its matching stable version. Consequently
`[1.0.0,2.0.0)` contains `2.0.0-rc.1` by precedence, but the explicit flag
still rejects it unless opted in. Authors wanting a narrower prerelease claim
should use an exact prerelease or narrowly bounded interval.

A prerelease module itself is experimental and must be described as such;
its own version does not automatically allow prerelease hosts/abstractions.

These rules classify declarations, not package solver behavior. NuGet restore
success alone does not prove a compatible Hoard composition. Do not assume the
NuGet.Versioning interval comparison implements the explicit Hoard flag.

### Dependency Availability and Optional Modules

Installed means included as a referenced package in the build; registered means
its declaration/type pairing has been recorded. Neither means enabled. Enabled
means selected to participate in the startup composition, not already activated
or ready. Selection and runtime validation belong to F-02/F-03, not F-01.

For each enabled declaring module, classify its dependencies as follows:

- A required target must be available and enabled, and satisfy its declared
  version range and prerelease flag; otherwise the composition is unsupported.
- An optional target that is absent or installed/registered but not enabled is
  unavailable. This alone is allowed, but the declaring module cannot claim
  that integration or capabilities supplied by the unavailable target.
- An enabled optional target must satisfy its declared range and
  `ModuleDependency.AllowPrerelease`, whether or not its author says the
  integration is "used". An incompatible enabled target makes the entire
  composition unsupported, just as a required dependency conflict does.

Do not automatically disable a module or optional integration, ignore the
dependency, or substitute a provider to turn an incompatible selected composition
into a supported one. Operators must explicitly change selection or install a
compatible version and revalidate. An unavailable optional target contributes no
active dependency edge; it is not activated implicitly. Enabled targets still
have their own host/abstractions compatibility obligations.

F-01 classification examples must distinguish these outcomes. F-02/F-03 must
reject unsupported selected compositions at startup with actionable, sanitized
diagnostics identifying the declaring module, dependency, and range/prerelease
conflict. F-01 registration neither enables modules nor performs this validation.

## Source, Binary, and Behavioral Compatibility

A stable change is nonbreaking only when existing consumers **and**
implementers remain source-compatible, previously compiled supported modules
remain binary-compatible, and documented behavior/invariants remain valid.

| Change | Classification | Required transition and guidance |
| --- | --- | --- |
| Documentation correction with unchanged agreement | Patch | Clarify without silently changing obligations |
| New independent optional type/API, no new required members or stronger obligations | Minor on stable contracts | Demonstrate existing consumers/implementers still work |
| Remove/rename a public member, change signature/type, narrow accepted inputs | Breaking | Stable major; explicit provider/host upgrade instructions |
| Add a required interface member or required declaration field | Breaking for implementers | Stable major even if some consumers compile |
| Add stricter publication/auth/behavior obligations or change observable semantics | Breaking | Stable major; behavioral migration notes and evidence |
| Change assembly identity or binary surface so old supported binaries cannot load/call | Breaking binary change | Stable major, rebuild/recompile guidance as applicable |
| Any breaking contract change before 1.0 | Breaking pre-1.0 | Explicit minor transition, e.g. 0.1 to 0.2; update ranges and migration guide |

Before 1.0, patch changes still must be nonbreaking. A provider must not declare
blanket `0.x` compatibility merely because it is prerelease or experimental.
For example, a provider built for `[0.1.0,0.2.0)` is not supported on `0.2.0`
unless its author qualifies and updates the declaration. Stable providers may
claim a broader tested interval, but cannot infer an untested major transition.

An apparently additive default interface member or implementation change is
not automatically compatible: review all three axes, not just whether one
consumer compiles. Tightened safety guarantees cannot be bypassed to preserve
an obsolete provider's support claim.

## Classification Acceptance Matrix

The host and abstractions versions in this table are illustrative independent
releases, not current published Hoard versions. The other axis/dependencies
are assumed valid unless the row says otherwise.

| Case | Declaration / candidate | Expected classification |
| --- | --- | --- |
| C-01 stable-compatible | Both ranges `[1.2.0,2.0.0)`; host 1.4.0, abstractions 1.3.2 | Compatible on both declared axes |
| C-02 out-of-range | Host range `[1.2.0,2.0.0)`; host 2.0.0 | Unsupported |
| C-03 missing-range | Host or abstractions range missing/empty | Unsupported, never default to all versions |
| C-04 pre-1.0 boundary | Abstractions range `[0.1.0,0.2.0)`; abstractions 0.2.0 | Unsupported until explicit requalification/migration |
| C-05 stable-breaking change | Add required interface member at 1.4.0 | Invalid minor release proposal; requires major transition |
| C-06 pre-1.0-breaking change | Required member added from 0.1.3 to 0.1.4 | Invalid patch proposal; requires 0.2.0 and updated ranges |
| C-07 prerelease denied | Host range `[1.0.0,2.0.0)`; host 1.5.0-rc.1, flag false | Unsupported despite interval containment |
| C-08 prerelease opted in | Same interval/candidate; host flag true | Compatible on this axis; still experimental |
| C-09 lower-bound precedence | `[1.5.0,2.0.0)`; candidate 1.5.0-rc.1, flag true | Unsupported: lower than minimum |
| C-10 prerelease bound without flag | `[1.5.0-rc.1,1.5.0]`; candidate 1.5.0-rc.2, flag false | Unsupported; range text is not opt-in |
| C-11 independent flags | Both candidates prerelease, only host flag true | Unsupported on abstractions axis |
| C-12 exact / metadata | `[1.2.3]`; candidate 1.2.3+build.7 | Compatible by precedence |
| C-13 invalid interval | `(2.0.0,1.0.0]`, `(1.0.0,1.0.0)`, `1.*`, or `[1.0.0,)` | Unsupported malformed/disallowed declaration |
| C-14 dependency | Required module absent or present outside its interval | Unsupported composition, no fallback |
| C-15 optional dependency | Optional module absent | Absence alone is allowed; never claim unavailable capability |
| C-16 behavioral break | Tighten required commit visibility while keeping signatures | Breaking; migration/qualification needed |
| C-17 binary break | Previously supported compiled provider loses a referenced member | Breaking even if a recompiled consumer passes |
| C-18 module prerelease | Provider 0.1.0-beta.1, host prerelease, host flag false | Unsupported host; provider suffix does not grant opt-in |
| C-19 optional enabled compatible | Enabled A optionally requires B `[1.0.0,2.0.0)`; B 1.5.0 enabled | Compatible dependency; both modules still need valid platform ranges |
| C-20 optional enabled incompatible | Enabled A optionally requires B `[1.0.0,2.0.0)`; B 2.0.0 enabled | Unsupported composition; no automatic module/integration disablement or substitution |
| C-21 optional dependency prerelease denied | Enabled A optionally requires B `[1.0.0,2.0.0)`; B 1.5.0-rc.1 enabled; dependency flag false | Unsupported composition despite interval containment |
| C-22 optional dependency prerelease allowed | Same interval/candidate and enablement as C-21; dependency flag true | Compatible dependency; still experimental, with other axes required to pass |
| C-23 optional installed but disabled | Enabled A optionally requires B `[1.0.0,2.0.0)`; B 2.0.0 installed/registered but not enabled | Treat optional target as unavailable; absence alone is allowed, with no B integration/capability claim or active dependency edge |

Automated examples in F-01 must classify interval/prerelease cases using these
explicit rules; release-change classification examples must explain source,
binary, and behavioral consequences. This is not the F-07 runtime support
matrix or a complete binary API-diff tool.

## Release and Migration Obligations

Before proposing a breaking contract release, record affected public members
and behaviors, consumer/implementer/binary impact, old/new ranges, provider
rebuild or code/config changes, qualification evidence, and rollback guidance.
Publish guidance with that release; never relabel an incompatible module as
supported or silently substitute another provider. Document unchanged cases
and limitations as well as required migrations.

F-02/F-03 must reject invalid compositions at startup using this policy.
F-07 adds reusable compatibility/conformance matrices. F-01's acceptance
classifier does not activate modules or certify their operational behavior.
