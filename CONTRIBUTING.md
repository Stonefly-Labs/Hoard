# Contributing to Hoard

Welcome! Hoard is currently in its **repository-foundation stage**, not a
working application. Start with the [README](README.md), [architecture](docs/ARCHITECTURE.md),
and [development workflow](docs/DEVELOPMENT.md).

## Local prerequisites

- Git and [GitHub CLI](https://cli.github.com/), authenticated with `gh auth login`.
- Python 3.11+ for repository-tool tests and checkpoint management.
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli)
  or another Copilot surface supporting repository agent skills, when using Spec Kit.
- OpenTofu 1.11+ and Azure CLI only for the optional infrastructure bootstrap.

Do not install a backend/UI toolchain or generate projects for documentation-only
work. Runtime versions, package-manager choice, and lockfiles belong to the
feature introducing those projects.

## Branch, change, document, publish

1. Start from current `main` on a purpose-named branch:
   `feature/001-provider-contracts`, `bugfix/cache-key-isolation`,
   `chore/tooling`, or `docs/setup`. Never work directly on `main`.
2. For product work, use the dependency-ordered [Spec Kit flow](docs/DEVELOPMENT.md#checkpointed-spec-kit-flow).
   Keep unrelated work out of the feature.
3. Add focused tests for changed behavior. Run the smallest relevant checks.
   Today: `python3 -m unittest discover -s tests/tooling -v`.
   For infrastructure: `tofu -chdir=infra/bootstrap fmt -check` and
   `tofu -chdir=infra/bootstrap validate` after initialization.
4. Update the README and all affected docs in the same branch **before merge**.
   If they are unaffected, explain why in the PR template.
5. Make a coherent commit, then immediately push:
   `git push -u origin HEAD` on the first push; `git push` thereafter.
6. When complete, push and open a PR targeting `main` with `gh pr create`.
   Supply scope, evidence, documentation impact, and operational risks.
   Never merge your own work unless a maintainer explicitly authorizes it.

Use concise, descriptive commit subjects, preferably
`type(scope): summary` (`feat`, `fix`, `chore`, `docs`, `test`, `refactor`).
Do not commit credentials, local state, deployment plans, downloaded artifacts,
or generated build output. Do commit dependency lockfiles.

## Documentation quality

Use task-oriented headings, short copyable commands, relative links, descriptive
link text, and accessible image descriptions. Distinguish **planned** behavior
from working features. Explain prerequisites, expected results, failure recovery,
and security implications for operational tasks. Use Mermaid when it clarifies
relationships; use restrained emoji and original/licensed SVG assets for navigation.
Do not put secrets or machine-specific identifiers in examples.

Architectural changes need a documented decision and compatibility impact.
Documentation should explain user/operator outcomes, not merely list files changed.

## Reporting issues

Use the bug or feature forms in [GitHub Issues](https://github.com/Stonefly-Labs/Hoard/issues/new/choose).
Include reproducible steps, expected behavior, environment, and sanitized logs.
For security concerns, **do not open a public issue containing exploit details
or credentials**. Use GitHub's private vulnerability reporting if the repository
has it enabled; otherwise contact a maintainer privately through their published
GitHub contact details. No private reporting channel is assumed to exist yet.
