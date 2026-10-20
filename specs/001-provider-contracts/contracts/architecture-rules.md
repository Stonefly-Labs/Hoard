# F-01 Architecture Acceptance Contract

**Status**: Implemented bounded source/package/metadata/IL checks exercised by
`bash scripts/validate-foundation.sh`; not runtime validation or a sandbox.
Names classify ownership; checks must inspect actual resolved relationships.

## Allowed Graph

| Source boundary | Permitted targets |
| --- | --- |
| Abstractions | BCL only |
| Core | Abstractions, BCL only in F-01 |
| Hosting | Abstractions, Core, DI abstractions; approved ASP.NET integration only when introduced later |
| Application | Core, Abstractions, approved public Hosting API |
| Protocol providers/slices | Core, Abstractions, approved public Hosting API |
| Metadata providers | Abstractions, private persistence framework/SDK |
| Artifact providers | Abstractions, private artifact SDK |
| Identity providers | Abstractions, approved public Hosting API, private identity SDK |
| Concrete Host / package-only custom-host fixture | Hosting, Application if used, explicitly referenced providers, host framework |
| Future console | HTTP management/capability schema only, no .NET module references |

Within F-01, the approved Hosting surface is only its builder/registration
types. No public HTTP integration is assumed to exist. Provider-private
framework dependencies are permitted inside the appropriate provider, never
as leaked public slice/shared contract types. Tests may inspect every boundary
but are never a runtime dependency. No provider references another concrete
provider, even of the same family; swaps are separate compositions.
An Identity provider's approved Hosting reference includes Hosting's transitive
Core dependency. This does not authorize direct Identity-to-Core references or
Core reached through an unrelated SDK/helper. Inspect Hosting-mediated and
other paths separately so an allowed route cannot hide a forbidden route to
the same node.
The BCL allowance does not permit `IQueryable`, `IDbConnection`/`IDbTransaction`,
or `DbConnection`/`DbTransaction` in shared public surfaces, including recursive
generic signatures.

## Inspection Inputs and Completeness

Use SDK-resolved restore graph/project metadata and `project.assets.json` for
the exact target/configuration, plus compiled assemblies read with test-only
Mono.Cecil. Inspect packed `.nuspec` dependencies and the independent consumers'
resolved assets too: a clean source graph does not prove a clean package.
Include declared project and resolved framework edges even if the compiler
emits no assembly use. Declared framework references require matching resolved
framework evidence.

Assign projects, packages, and assemblies explicit boundary ownership. Validate
identity rather than trusting prefixes or namespaces. Framework assemblies
are distinguished from third-party packages using resolved framework assets,
not a rule allowing all names starting `System` or `Microsoft`.
For Core/Abstractions in F-01, any non-BCL package outside Abstractions is
forbidden; this catches provider SDKs even through a neutral-looking helper.

Traverse the full dependency closure, public signatures (including nested
generics, constraints, bases/interfaces, attributes, arrays, fields, events,
properties, and methods), and compiled type/member/IL references. For slices,
map source folders to unique namespace roots and confirm their agreement, then
reject another slice's internal handler/type/member use even within the same
assembly. Compiler-generated nested/async types inherit their owning slice.
Public Core/Abstractions contracts remain the allowed coordination seam.

Do not resolve inspected assemblies by loading/executing provider code.
Unresolved references, missing build/restore inputs, duplicate ownership,
unmapped slice roots, or incomplete scans fail with actionable errors, not
empty success results. Limit the claim to the documented source/metadata/IL
checks: arbitrary reflection strings and malicious trusted code are not
sandboxed or exhaustively analyzed.
The real scan set must contain exactly the platform graph, all five independent
provider graphs, and both host graphs, with unique explicit scan identities.
Omitting any required scan is an inspection error.

## Rule and Negative-Evidence Matrix

Each case must have an isolated forbidden input and a permitted counterpart.
The check is accepted only after it demonstrably rejects the forbidden input.
Most negatives compile as separate test-only assemblies; cyclic project graphs
use isolated normalized graph data because normal restore rejects them first.
Never add a forbidden edge to the real product solution just to test a rule.

| Rule | Rejected case / isolated input | Permitted counterpart |
| --- | --- | --- |
| ARCH-001 | Abstractions references a concrete provider, SDK, persistence framework, or Hosting/HTTP type | BCL-only declarations and family markers |
| ARCH-002 | Core directly references any concrete provider or EF/SDK, including an unused declared reference | Core -> Abstractions |
| ARCH-003 | Core -> apparently neutral helper -> provider/EF/SDK, in resolved package or project closure | Provider-private SDK outside Core's closure |
| ARCH-004 | Shared contract or management/protocol slice surface leaks provider-private types, including nested generic/attribute/constraint forms | Public signatures use neutral Core/Abstractions types |
| ARCH-005 | Protocol references storage/persistence provider, or any concrete provider references another | Independently compiled providers reference permitted contracts |
| ARCH-006 | Package/project dependency cycle | Full acyclic permitted graph |
| ARCH-007 | One management/protocol slice uses another slice's internal handler/type/member, including same-assembly IL/async use | Slices call public shared Core/Abstractions contracts |
| ARCH-008 | Application leaks/uses private EF/provider internals, or an otherwise unapproved package edge bypasses the table | Application -> Core/Abstractions/approved Hosting |

Exercise direct and transitive negatives, declared-but-unused references, and
packed dependency negatives. An assembly-only scan is insufficient. For
ARCH-004 include both a direct public type leak and a recursively nested leak.
For ARCH-007 include same-assembly handler invocation; namespace presence alone
must not fail an otherwise isolated slice.

## Diagnostics and Failure Semantics

A violation identifies the rule, source/target boundary and resolved identity,
member or manifest location, and the dependency path for transitive failures.
Example shape:

```text
ARCH-003: Hoard.Core -> Helper -> Fixture.Persistence -> EF
source: Hoard.Core; target: Fixture.Persistence; location: resolved dependency graph
Core may depend on Abstractions and BCL only; remove the forbidden path.
```

This is an output contract, not a claim about current scanner output.
Inspection errors are separate from confirmed violations, but both fail the
acceptance command with a nonzero exit code. Do not swallow resolver exceptions,
invent missing metadata, ignore an unknown SDK, or pass after scanning nothing.

## Scope Limits

These checks protect compile/package boundaries, not semantic correctness of
provider code. Actual startup rejection, disabled endpoints/workers, readiness,
atomic publication, cancellation, storage recovery, normalized authorization,
and native-client compatibility require their own later tests. F-01 introduces
neither provider certification nor runtime isolation.
