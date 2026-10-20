# Test layout

`tooling/` contains executable Python standard-library tests for the repository
checkpoint/release helpers:

```bash
python3 -m unittest discover -s tests/tooling -v
```

F-01 introduces three .NET 10 test projects:

| Project | Bounded evidence |
| --- | --- |
| `unit/Hoard.Foundation.Tests` | Declaration compiler cases, registration without construction, C-01 through C-23 compatibility/release obligations |
| `architecture/Hoard.Architecture.Tests` | Declared/resolved/packed/compiled dependency graph including unused framework references, recursive public surface including prohibited BCL shapes, slice IL, ARCH-001 through ARCH-008 negatives and permitted graph, mandatory eight real scans and explicit inspection failures |
| `integration/Hoard.Composition.Tests` | Isolated Core, five independent package/family consumers, package source/hash provenance, baseline/replacement custom hosts |

Run `bash scripts/validate-foundation.sh`. Tests require its
`HOARD_FOUNDATION_EVIDENCE` manifest and fail explicitly if it is absent.
They inspect generated files rather than invoking the script or executing
providers. The only executed compatibility input is a tiny synthetic binary
caller demonstrating a removed member; neither custom host is executed.
Standalone `fixtures/` and `examples/CustomHost` projects stay outside
`Hoard.slnx`, are copied outside repository props inheritance, and carry locks.
Architecture and compatibility fixture trees carry their own complete props.
The orchestrator verifies their formatting separately.

The script's `--phase declarations`, `--phase packages`, `--phase architecture`,
and `--phase hosts` selectors provide focused partial checks. The default full
run is required for acceptance. See the [quickstart](../specs/001-provider-contracts/quickstart.md).
Architecture checks protect declared/resolved metadata, signatures and IL;
reflection strings and malicious trusted code are not sandboxed or exhaustively
analyzed. Synthetic SDK types exercise leakage without introducing EF or a
real vendor dependency into the product.

`conformance/` and `protocols/` remain reserved. Provider conformance must
eventually exercise every advertised implementation; protocol tests must use
real native package clients. Compile-only fixtures do not satisfy either gate.

OpenTofu mock-provider tests live beside the bootstrap at
`infra/bootstrap/tests/` and run with `tofu -chdir=infra/bootstrap test`.
