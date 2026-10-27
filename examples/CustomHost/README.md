# Compile-only custom host

This example proves public package references and explicit registration.
It never calls `Build`, `Run`, `Start`, or route mapping. **Do not run it as a
cache**: the four providers are fixtures, not functional implementations.

## Prerequisites and packages

Use Git, Python 3.11+, Bash, and a stable .NET 10 SDK satisfying the repository's
`global.json`. Package restore needs trusted access to nuget.org. No external
database, cloud, Docker, Node, upstream registry service, or credentials are needed.

The example explicitly references `Hoard.Hosting`, `Hoard.Fixtures.Protocol`,
`Hoard.Fixtures.Metadata`, `Hoard.Fixtures.Artifact.One`, and
`Hoard.Fixtures.Identity`, all exact `[0.1.0]` local acceptance packages.
`Hoard.Abstractions` and `Hoard.Core` are transitive platform dependencies;
Hosting also brings DI abstractions 10.0.13. `Hoard.Fixtures.Artifact.Two` is an
independently built alternative, not a dependency of One.
These packages are not published. The project has no ProjectReference, source
imports, or friend access and carries complete independent settings and a lock.
SDK package pruning is disabled to preserve the explicit packed dependencies
for this acceptance inspection, even when ASP.NET supplies equivalent assemblies.

## Reproduce the proof

From the repository root:

```bash
bash scripts/validate-foundation.sh
# Focused registration/host/package/boundary checkpoint, not full acceptance:
bash scripts/validate-foundation.sh --phase hosts
```

The Bash wrapper creates a private, resolved `hoard-foundation.*` temporary
directory and removes only that directory on exit, including failures.
The Python helper copies source inputs without `bin`/`obj`, builds Core with
only Abstractions reachable, packs four platform libraries into `feed/`, and
copies/builds/packs each of five provider fixtures separately. Family-typed
consumers use those packages, not source. Private `source-cache/`, `cache/`,
and per-project replay caches prevent stale published packages satisfying proof.

The generated `NuGet.Config` clears inherited sources and explicitly defines
the private `feed/` and `https://api.nuget.org/v3/index.json`. Source mapping sends
`Hoard.*` only to the local feed, with `*` on nuget.org for external dependencies.
Tests compare actual package cache source metadata and SHA-512 hashes against
the freshly packed local archives. Source paths and Git revision stamps do not
change these local acceptance package identities between clean runs.
The helper also canonicalizes ZIP timestamps/attributes and OPC metadata
relationship IDs/paths in unsigned local archives while preserving nuspec,
core-property, and assembly payload bytes. It refuses signed/external packages.
This local proof step is not a release packaging/signing pipeline. SDK/compiler
changes affecting payloads still require reviewed lock updates.

To retain evidence temporarily for manual inspection, use the same helper in
your own bounded shell, with explicit cleanup:

```bash
work="$(mktemp -d "${TMPDIR:-/tmp}/hoard-foundation.XXXXXXXX")"
work="$(cd "$work" && pwd -P)"
trap 'python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1])" "$work"' EXIT
python3 scripts/foundation_evidence.py "$PWD" "$work"
```

The helper's baseline steps copy `examples/CustomHost/` to `hosts/One/` outside
repository build-prop inheritance, then execute:

```bash
export NUGET_PACKAGES="$work/cache"
dotnet restore "$work/hosts/One/CustomHost.csproj" \
  --configfile "$work/NuGet.Config" --locked-mode
dotnet build "$work/hosts/One/CustomHost.csproj" \
  --configuration Release --no-restore
```

The output is `hosts/One/bin/Release/net10.0/CustomHost.dll`; the replacement
is `hosts/Two/bin/Release/net10.0/CustomHost.dll`.
Each host has `obj/project.assets.json` and `packages.lock.json`.
`evidence.json` records assemblies, package/restore inputs, and before/after
platform/unrelated-provider source hashes for tests. Tests consume the
`HOARD_FOUNDATION_EVIDENCE` path set by the helper. Nothing is published or run.
When the shell exits, the trap removes this named temporary directory.

## Replace the artifact fixture

The second copied host changes only:

1. `Hoard.Fixtures.Artifact.One` to `Hoard.Fixtures.Artifact.Two` in the project.
2. The using namespace and `ArtifactOneProvider` registration/declaration to
   `ArtifactTwoProvider` in `Program.cs`.
3. Its derived lockfile, explicitly regenerated for the new PackageReference
   and then replayed in locked mode.

Both declarations use the logical module ID `fixture.artifact`, Artifact category,
and compatible platform ranges. They belong in **separate** compositions,
never together. Neither package references the other. No Core or unrelated
provider source changes. This proves composition, not equivalent byte-store
behavior. After intentional source/dependency changes use
`bash scripts/validate-foundation.sh --update-locks`, review the changed locks,
then require the default locked run to pass. Never skip lock/provenance failures.

## Registration and support limits

`Program.cs` calls `WebApplication.CreateBuilder`, `AddHoard`, and four generic
`AddModule` registrations. Hosting records declarations/types in DI without
constructing providers, mapping HTTP, enabling modules, validating compatibility,
selecting stores, resolving secrets, or reporting readiness.
The unit acceptance uses a throwing provider constructor to protect that boundary.

A future curated runtime configures already bundled providers. Adding a provider
to a custom operational runtime requires explicit package reference/registration,
rebuild, redeploy, and restart. Trusted in-process modules are not sandboxed:
no arbitrary assembly loading, runtime package installation, hot swap, or
marketplace exists. Compilation is not protocol/native-client compatibility,
store integrity, operational support, or certification.
See the [provider guide](../../docs/PROVIDERS.md).

F-04 does not change this example's compile-only purpose or enable discovery
implicitly. The separate [LifecycleHost discovery variants](../LifecycleHost/README.md#protected-discovery-variants)
exercise protected reads, same-binary restart and a rebuilt custom distribution
through local packages. Application consumers additionally require the
ASP.NET Core shared framework; non-web package propagation is tested separately.
Adding a package or marker here supplies no tested support, readiness or
execution permission and does not turn this host into a runnable product.

F-05 leaves this marker-only example unchanged. Its new operational interfaces
are opt-in, not additional marker members. The separately compiled
[metadata fixture consumer](../../tests/fixtures/metadata/Consumer/MetadataConsumer.cs)
uses only `IMetadataStore`/schema/publication contracts for its journey, with
[host adapters](../../tests/fixtures/metadata/HostAdapters/) selecting SQLite or
memory and using the existing lifecycle/configuration gate. Run
`bash scripts/validate-metadata.sh` for same-binary composition, old marker-binary
compatibility and separately attributed L/D proof. Registration here neither
opens metadata nor grants publication, recovery or deletion permission. No
production SQLite/PostgreSQL composition API is supplied by these fixtures.

There are no migrations, runtime state, infrastructure changes, permissions,
release tags, or deployments here. Roll back source and matching locks together
through a reviewed change; the script's feeds, caches, binaries, and manifests
are temporary and must not be committed.

F-07's separate test-only conformance Host is not this compile-only example.
Its package-mode consumer explicitly references the packed
`Hoard.Fixtures.Conformance.Host` and exercises both SQLite/Local and
Memory/ObjectSemantics using one unchanged consumer image and TestServer.
These component rows observe initialization, readiness, in-process declaration/
lifecycle probes, disabled-store inactivity and complete stop. They do not
certify providers, implement a production protocol/identity system, or supply a
qualifying composition CLI. The two rows now emit bounded, owner-linked safe
snapshots with independent input/image/stage validation; this diagnostic check
does not complete remaining composition transport, inherited inventories or
profile evaluation.
Shared packaged ownership callbacks additionally cover cancellation, retained
initialization and shutdown late faults, without treating finite caller return
or eventual callback settlement as a released lifecycle root. All seven rows now
have independently checked safe observations; this does not supply native child
containment or a complete qualifying profile.
The initializer-failure row extends actual safe component admission to ten
proofs/twenty-one snapshots. The separate native diagnostic records an owned
command and checks process-resource cleanup, not module-root qualification.
Its first Linux attempt rejects writable command inputs; its sealed successor
then rejects test output through the build projector. The corrected test
projector passes Linux native replay at exact `e9a1589`. Distinct actual owners now cover schema denial
and corrupt-manifest recovery with repaired worker entry, bringing safe component
admission to thirteen proofs/thirty-three snapshots. This compile-only
custom-host example is unchanged. The separate short native diagnostic workflow
does not qualify SQLite provenance, which remains explicitly unobserved.
Exact `f6e9db4` passes all thirteen selected native cases with actual
process-resource release, closing bounded T044 probes, not the qualifying
composition profile. Shared Host authority/guarantee admission and active-request
controls now pass all four CP-19/20 package cases, preserving denial before store
I/O and settled explicit restart. Their safe transport/full-profile integration
remains open; this compile-only custom-host example is unaffected.
