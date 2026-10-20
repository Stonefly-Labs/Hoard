# Test layout

`tooling/` contains executable Python standard-library tests for the repository
checkpoint/release helpers:

```bash
python3 -m unittest discover -s tests/tooling -v
```

`unit/`, `integration/`, `architecture/`, `conformance/`, and `protocols/`
are reserved for product tests introduced by future specifications. They are
not test projects yet. Provider conformance must exercise each advertised
implementation; protocol tests must eventually use real native package clients.

OpenTofu mock-provider tests live beside the bootstrap at
`infra/bootstrap/tests/` and run with `tofu -chdir=infra/bootstrap test`.
