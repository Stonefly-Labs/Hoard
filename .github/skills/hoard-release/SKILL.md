---
name: hoard-release
description: Prepare and publish an explicitly authorized Hoard SemVer tag-driven GitHub source release, separate from builds and deployment.
---

# Hoard source release

Read `docs/RELEASING.md` and `.github/copilot-instructions.md`.
Use this skill when a maintainer explicitly asks for a release, or when
`hoard-speckit` invokes it at `await_merge` under the documented standing
authorization for the derived `v0.0.X-alpha` source prerelease. Never create
a release tag simply because implementation/bootstrap is finished.

1. Confirm the requested exact version and authorization to push its tag. If
   missing, ask; do not infer `v0.1.0` from repository state. For the Spec Kit
   handoff, verify the pinned directory's derived version and recorded merged
   feature PR; that handoff supplies authorization without another prompt.
2. Ensure the release/docs changes have passed review and merged to `main`.
   If documentation must change, do it on a work branch, commit/push, and open
   a PR; stop until merged. Never commit release changes on main.
3. Fetch main/tags. Require a clean worktree. Resolve an explicit reviewed
   `origin/main` commit; never implicitly tag the current feature branch.
   For Spec Kit, require the exact feature PR merge commit reachable from
   `origin/main`, even when main has advanced.
4. Run `python3 scripts/release.py VERSION` for syntax and
   `python3 -m unittest discover -s tests/tooling -v`.
   Ensure the version/tag/release does not already exist locally/remotely.
   Verify README/docs describe available versus planned behavior truthfully.
   Exception for an interrupted Spec Kit handoff: verify an existing annotated
   tag resolves to the exact requested merge commit locally/remotely. If only
   local, push only that verified tag; if remote, skip creation/push and observe
   its existing run. A matching published prerelease may be reused after all
   publication checks; a collision blocks, never overwrite it.
5. Create an **annotated** tag at that exact commit:
   `git tag -a VERSION COMMIT -m "Hoard VERSION"`.
   Run `python3 scripts/release.py VERSION --check-main`.
   Push only that tag with `git push origin refs/tags/VERSION`; never `--tags`,
   `--force`, or moving/replacing an existing release tag.
6. Observe the `Source release` Actions run and resulting GitHub Release.
   Check prerelease classification, generated notes, source archives, and the
   intended commit. Report failure explicitly; do not claim publication based
   on a successful tag push alone.
   If a correct remote tag has no release, diagnose/watch or rerun its specific
   failed run when appropriate; never move the tag or silently edit a release.

The tag workflow publishes source archives/release notes only. No build,
NuGet/npm/container publication, Azure login, infrastructure apply, or deployment
is authorized or performed. Runtime binaries/SBOM/signing require a later spec.
Never silently edit an existing release during a rerun.
