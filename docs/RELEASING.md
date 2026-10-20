# Source releases from Git tags

**Release publication is separate from CI/CD and deployment.** The bootstrap
supports GitHub source releases only, because there is no product to build yet.

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
maintainer authorization and an exact version; finishing a feature is not
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
