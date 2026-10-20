# F-01 Validation Quickstart

**Design-stage guide**: Product commands and paths below are planned, not
available now. Run them only after the implementation stage introduces them.
Successful compilation proves contract usability, not a runnable cache,
production provider, protocol compatibility, activation, or certification.

## Current Planning Check

The existing repository-tool check is:

```bash
python3 -m unittest discover -s tests/tooling -v
git diff --check
```

No product solution, .NET build, provider, or host exists at this checkpoint.
Do not scaffold one merely to execute the future commands.

## Planned Prerequisites

Use Git, Python 3.11+, Bash, and a stable .NET 10 SDK satisfying the planned
`global.json` baseline/roll-forward policy. On Windows use a Bash-capable shell
for the orchestration script; the .NET projects themselves are not Bash-specific.
The first external tool/test dependency restore needs access to nuget.org.
Thereafter use locked restore with an available package cache/feed.

No cloud account, external DB, Docker, live upstream registry, credentials,
Node runtime, or production NuGet package publishing is needed.
Track exact direct pins centrally and applicable restore lockfiles; do not
commit build output or local feed/cache contents.

## Planned Full Foundation Check

The implementation must introduce one bounded orchestration entry point:

```bash
bash scripts/validate-foundation.sh
```

It must fail on any failed subprocess and report which proof failed, preserve
diagnostics without secrets, and clean only its own temporary paths. Its
documented steps are:

1. Restore the solution with tracked lockfiles, build Release, and verify
   SDK formatting/analyzers without changing files.
2. Restore/build Core independently with only its project and Abstractions
   reachable; inspect the complete resolved closure. Neither restoring a
   solution containing providers nor building with `--no-dependencies` is
   an adequate provider-free proof.
3. Pack the four platform libraries as local `0.1.0` acceptance packages into
   a fresh private temporary feed. No push/publish command is involved.
4. Copy each of the five standalone provider fixture projects into isolated
   work directories outside repository build-prop inheritance, then restore/
   compile/pack them using platform PackageReferences only. Give the commands
   explicit local-feed and nuget.org sources and an isolated package cache.
   Do not accept a cached published Hoard package instead of the just-built one.
5. Copy the self-contained custom-host example outside the platform source
   graph, restore/build using only packaged platform/fixture inputs, and
   inspect the resolved assets and output. Do not run it.
6. Build a second copied host after changing only the artifact fixture package
   reference and registration type/declaration from One to Two. Confirm the
   platform and unrelated provider source inputs are unchanged.
7. Run unit, architecture, compatibility, and composition acceptance tests.
   Show every isolated forbidden case is rejected for the intended rule, while
   the permitted graph and both host variants pass.

Standalone fixture and example projects must carry their own complete build/
dependency settings; no `Directory.Build.props` imports, friend assembly grants,
source links, absolute platform paths, or ProjectReferences may mask missing
package assets. Their ordinary packages may have their normal SDK dependencies
only where the architecture allows; these simple fixtures need none.
Track/replay locks for consumers where applicable and compare packed dependency
metadata with their resolved closure.

## Planned Focused Commands

After implementation, the normal source-graph checks are:

```bash
dotnet restore Hoard.slnx --locked-mode
dotnet build Hoard.slnx --configuration Release --no-restore
dotnet format Hoard.slnx --verify-no-changes --no-restore
dotnet test Hoard.slnx --configuration Release --no-build --no-restore
```

These commands alone do not prove package independence or replacement; the
orchestrator additionally performs the isolated pack/consumer scenarios above.
It also verifies formatting for standalone fixture/example projects, which
are deliberately outside the source-graph solution.
The implementation must document its exact local feed configuration, package
IDs, copy/build commands, output paths, and rerun/cleanup procedure in the
example guide. Never treat the planning commands as passing evidence today.

## Expected Evidence

| Proof | Expected result |
| --- | --- |
| Core-only restore/build and closure scan | Pass with Abstractions/BCL only; no concrete provider/EF/SDK restored |
| Four families plus second artifact fixture | Five packages compile independently against public package APIs |
| Custom-host baseline and replacement | Both compile; no platform edits, private APIs, or external service |
| Declaration inspection/registration | Metadata and recorded types available; throwing provider constructor never called |
| Architecture positives/negatives | Permitted graph passes; each `ARCH-001` through `ARCH-008` negative rejects with source/target/rule |
| Compatibility examples | Every `C-01` through `C-18` case receives the documented classification |
| Documentation review | Every fixture/example is compile-only; no operational support or certification claim |

See [architecture rules](contracts/architecture-rules.md) for transitive,
signature, cycle, and same-assembly slice cases, and
[compatibility policy](contracts/compatibility.md) for version interpretation.
Reject missing inputs or unexpected classifications rather than skipping them.

## Composition and Support Limits

The future example explicitly registers already referenced fixture packages
through [the public Hosting API](contracts/public-api.md). It must not call
`Build`, `Run`, `Start`, or map routes, and must not promise initialization or
safe package downloads. The artifact replacement proves independent contract
consumption, not that two stores behave equivalently.

A future curated distribution selects already bundled providers via validated
configuration. A future custom distribution adds explicit package references
and registrations, rebuilds, redeploys, and restarts. Providers are trusted
in-process application code; no arbitrary assembly loading, runtime downloads,
hot replacement, sandbox, or marketplace exists.

## Failure, Cleanup, and Handoff

Missing SDK/packages, restore/pack failure, unresolved inspection input,
forbidden dependencies, unexpected negative-case success, or example build
failure blocks F-01 acceptance. Fix the actual issue; do not bypass a check,
silently use another package, or describe the fixture as supported.

Only generated files in the check's resolved temporary work directory may be
cleaned automatically. Keep lockfiles tracked and secrets/build/feed contents
untracked. There is no data migration, infrastructure plan/apply, release, or
deployment to roll back.

At planning completion, the next stage is custom requirements-quality checklist
generation. Task generation, read-only analysis, reviewer-owned checklist
approval, implementation, convergence, and finalization remain separate gates.
