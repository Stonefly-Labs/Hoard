# Hoard contributor and Copilot instructions

## Scope and sources of truth

- Hoard is an MIT self-hosted pull-through cache, not a private publishing registry.
- This bootstrap contains foundations only. Do not generate a .NET solution,
  Next.js application, package manifests, runtime, product CI/CD, or cloud resources
  unless the current feature/request explicitly calls for them.
- Read `docs/PRODUCT_CHARTER.md`, `docs/PRODUCT_SPEC.md`,
  `docs/ARCHITECTURE.md`, `docs/adr/0001-modular-provider-architecture.md`,
  and the active `specs/<feature>/` artifacts.
  `.specify/memory/constitution.md` defines project governance at v1.0.0.
  Its initial adoption PR must merge before the first feature spec begins.
- Prefer the simplest complete change. Do not turn planned APIs or dependencies
  in the design documents into implemented claims.

## Mandatory Git and documentation workflow

- All work must be on `chore/`, `feature/`, `bugfix/`, `hotfix/`, `docs/`,
  `refactor/`, `test/`, or another explicit type-prefixed branch. Never commit
  directly on `main`, a detached HEAD, or a release tag.
- Inspect branch and worktree first; preserve unrelated/uncommitted user changes.
  Stay on a user-specified correct branch. Spec directories and branches are
  independent: e.g. `feature/001-provider-contracts` with
  `specs/001-provider-contracts`. Do not modify vendor Spec Kit to enforce names.
- Commit coherent work with a descriptive subject; **push immediately after each
  commit**. Establish upstream with `git push -u origin HEAD`. Report failed
  pushes rather than claiming the checkpoint is shared.
- On completion, update the README and all affected guides/examples/diagrams
  **before merging the PR**; explain explicitly if a document is unaffected.
  Keep claims honest about current versus planned behavior.
- Run relevant checks, commit, push, and create/update a PR targeting `main`
  using the repository template. Do not merge without explicit authorization.
- Do not apply infrastructure, change repository governance/settings, create
  release tags, or publish a release unless explicitly authorized for that action.
  Creating IaC files is not permission to run `tofu apply`.

## Planned development stack and boundaries

- .NET 10, ASP.NET Core Minimal APIs, built-in DI, OpenAPI, OpenTelemetry.
  Use nullable-aware types, asynchronous bounded streaming, cancellation,
  actionable errors, and sanitized diagnostics.
- NuGet-distributed modules: Abstractions, Core, Hosting, Application, concrete
  Host; Protocols/Persistence/Storage/Identity provider families.
- Core depends on Abstractions, never EF Core, DbContext, or concrete providers.
  EF Core and schemas/migrations are private to relational persistence modules.
- Use vertical slices for management operations and protocol-specific endpoints.
  No cross-slice internal handler calls or mandatory MediatR/CQRS.
- Centralize cache identity/auth partitioning, freshness, verified atomic
  publication, streaming, single-flight, safe GC, SSRF policy, and telemetry.
  Do not duplicate these invariants in endpoint slices.
- Providers are trusted in-process code composed at build time and validated
  at startup. No arbitrary assembly loading or silent provider fallback.
- First distribution: NuGet v3, SQLite, filesystem, single node.
- UI: latest supported stable Next.js at implementation time, App Router,
  TypeScript, Tailwind, shadcn/ui; accessible polished dark/light experience.
  Default static export served by .NET: no server actions, SSR, or Node-only API
  routes in the bundled console. Consume management APIs/capabilities.
- Azure is optional deployment infrastructure, never a personal-use dependency.
  OpenTofu owns infrastructure; environment-scoped GitHub OIDC, no client secrets.

## Skills and agents: use the documented entry points

- **`hoard-speckit`** (`.github/skills/hoard-speckit/SKILL.md`): use when asked
  to advance/resume the backlog. Exactly one stage per invocation, durable
  checkpoint, dependency-aware selection. Never start it merely because
  bootstrap/doc work mentions Spec Kit.
- Delegate each Spec Kit stage to its existing `speckit-*` skill; do not
  reimplement the command prompts. `speckit-analyze` stays read-only and
  custom checklist review stays reviewer-owned.
- **`hoard-architecture-review`** (`.github/agents/hoard-architecture-review.agent.md`):
  use for substantial changes to project references, provider contracts,
  module composition, or shared cache invariants before PR handoff.
  Not required for simple documentation/tooling changes.
- **`hoard-release`** (`.github/skills/hoard-release/SKILL.md`): use for an
  explicitly requested release. Validate tag and main ancestry; tags publish
  source releases only, never deployment.
- Read `docs/DEVELOPMENT.md` for invocation, stage gates, recovery, and handoff.
  Do not launch fleets or multi-agent workflow engines as part of these skills.

## Validation and safety

- Repository tools: `python3 -m unittest discover -s tests/tooling -v`.
- IaC: `tofu -chdir=infra/bootstrap fmt -check`, `init -backend=false`,
  `validate`, and `test` (mock providers; no Azure/GitHub changes).
- When product projects arrive, introduce and document focused format/type,
  unit, architecture, provider-conformance, and native-client protocol checks.
  Do not pretend these commands exist before they do.
- Keep lockfiles tracked, including `.terraform.lock.hcl`. Keep `.env`, tfvars,
  state/backups, plans, tokens, and runtime data out of Git. Never log credentials.
- Use least privilege. Release workflow needs no Azure permissions or secrets;
  future deployment workflows must select the matching GitHub environment and
  grant `id-token: write` only to the deployment job.
