# Source releases from Git tags

**Release publication is separate from CI/CD and deployment.** The bootstrap
introduced GitHub source releases only. The current tag workflow still does not
build or distribute runtime binaries, even though foundation libraries now exist.

## What the tag workflow does

Pushing `vMAJOR.MINOR.PATCH` or
`vMAJOR.MINOR.PATCH-prerelease.identifiers` triggers
[Source release](../.github/workflows/release.yml). It:

1. Validates the tag using `scripts/release.py` (SemVer without build metadata).
   Core/numeric prerelease identifiers cannot have leading zeroes.
2. Verifies that the tagged commit is reachable from the current `origin/main`.
   Tags from unmerged feature branches fail.
3. Publishes a GitHub Release with generated notes and GitHub's automatic
   `.zip`/`.tar.gz` source archives. `-alpha.1`, `-beta.1`, `-rc.1`, etc. are
   prereleases and cannot become Latest. Stable releases use GitHub's normal
   latest-release selection.

There is **no** build, app test pipeline, binary/package/container publication,
Azure credential, `id-token: write`, environment selection, infrastructure
apply, or deployment. The only elevated permission is `contents: write` on the
release job, using its short-lived repository `GITHUB_TOKEN`.

## Maintainer procedure

Use the `hoard-release` skill for assisted releases. A release requires explicit
maintainer authorization and an exact version. The Spec Kit flow has the bounded
standing authorization below; outside that flow, finishing a feature is not
authorization to tag.

1. Update README/release/upgrade docs on a purpose-named branch, commit/push,
   and merge the reviewed PR before tagging. Release notes must distinguish
   planned capabilities from working ones.
2. From a clean checkout, fetch and choose a reviewed main commit:

   ```bash
   git fetch origin main --tags
   git status --short
   git log -1 --oneline origin/main
   python3 -m unittest discover -s tests/tooling -v
   python3 scripts/release.py v0.1.0-alpha.1
   ```

   The version below is an **example**, not a reserved first release.
   Check both local/remote tags and existing GitHub releases before choosing it.

3. Create an annotated tag at the reviewed commit (replace `COMMIT_SHA`):

   ```bash
   git tag -a v0.1.0-alpha.1 COMMIT_SHA -m "Hoard v0.1.0-alpha.1"
   python3 scripts/release.py v0.1.0-alpha.1 --check-main
   git push origin refs/tags/v0.1.0-alpha.1
   ```

4. Verify publication, not just the push:

   ```bash
   gh run list --workflow release.yml --event push --limit 5
   # Inspect/watch the run associated with your exact tag.
   gh release view v0.1.0-alpha.1
   ```

   Confirm the commit, source archives, generated notes, and prerelease status.
   No application install instructions or runtime binaries should be implied.

## Spec Kit post-merge alpha releases

The maintainer has authorized `hoard-speckit` to invoke `hoard-release` during
`await_merge`, after the recorded feature PR has merged and before recording
completion or moving to another spec. No additional release confirmation is
required for that handoff. It authorizes only the derived source prerelease;
it does not authorize merging PRs, other versions, packages, or deployment.

The version is **`v0.0.X-alpha`**, with X taken from the pinned spec directory's
positive numeric prefix, without leading zeroes:

| Spec directory | Release tag |
| --- | --- |
| `specs/001-provider-contracts` | `v0.0.1-alpha` |
| `specs/002-module-lifecycle` | `v0.0.2-alpha` |
| `specs/010-example` | `v0.0.10-alpha` |

These illustrate the mapping, not releases already published. Backlog IDs and
dependency order do not determine X. Do not drop `-alpha` or change numbering
without a new maintainer decision. Previously completed specs are not
retroactively tagged or released by this change.

Use `python3 scripts/speckit_flow.py status` to obtain the active `release_tag`.
The target is the recorded feature PR's **exact merge commit**, verified in
fetched `origin/main`, not the progress branch's tip or a later main commit.
Follow the maintainer procedure above with that version and commit, including
the annotated tag, tooling checks, and publication verification. Commit/push
the running progress checkpoint before invoking the release skill to preserve
its clean-worktree requirement.

If interrupted, inspect existing local/remote tags and publication before
acting. A correct local-only annotated tag can be pushed; a correct remote tag
must not be recreated or moved. Watch its run or rerun that specific failed
run when appropriate. A matching already-published prerelease can be reused
after verifying notes, archives, classification, and commit; do not edit it.
A collision, draft, non-prerelease, wrong commit, failure, or absent release
blocks completion, leaving the stage running.

Only after verification may `speckit_flow.py finish` record `release_tag` and
`release_url` alongside the merged completion. It independently checks the
annotated remote tag's peeled commit and the published GitHub prerelease.
Commit/push the completion and publish its progress PR; that PR must merge
before another invocation starts a new specification. Publication is part of
the existing `await_merge` stage, not permission to run the next stage.

## Failure and rollback

- A malformed tag or a commit outside main fails before release publication.
  Diagnose the run rather than bypassing validation.
- An existing release causes publication to fail rather than silently changing
  its content. Inspect the existing release before considering any manual action.
- If a run fails before a release exists, resolve the cause and rerun that
  specific workflow run when appropriate; do not move the tag.
- Never force-push/move a published version tag. Correct an erroneous release
  with a new version and a clear notice. A maintainer may explicitly choose
  to mark an unsafe release as draft; this is not an automatic rollback.
- Nothing was deployed, so rolling back a release does not roll back an
  environment. Future deployment rollback will have its own workflow.

Tag rulesets/protection, required reviews, signed tags, SBOMs, provenance,
reproducible binaries, package publishing, and distribution signing can be
proposed separately. This bootstrap does not change repository governance
settings or claim those capabilities are implemented.
