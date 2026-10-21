---
name: hoard-speckit
description: Advance or resume Hoard's dependency-ordered Spec Kit backlog, one checkpointed stage per invocation, beginning with the constitution.
---

# Hoard Spec Kit driver

Use this skill when the user asks to advance/resume the Hoard specification
backlog. **One invocation executes at most one stage.** Do not call this skill
recursively or launch a fleet/workflow engine. This is not permission to build
unrequested features, apply infrastructure, or merge PRs. An `implement` stage
covers **all** remaining spec tasks, not one task or batch. An `await_merge`
invocation includes the authorized post-merge alpha source release below.

## Load and reconcile

1. Read `.github/copilot-instructions.md`, `docs/DEVELOPMENT.md`, and run
   `python3 scripts/speckit_flow.py status` from the repository root.
   The tracked `.specify/hoard-flow.json` is authoritative progress.
2. Inspect branch, worktree, and upstream. Never overwrite unrelated work.
   Fetch `origin/main` before making a new feature/progress branch.
   Before starting a **new** spec, ensure the current checkpoint and ratified
   constitution are already in `origin/main`; if they are only in an open PR,
   stop at that merge gate. Do not start dependent work from an unmerged branch.
3. If status is `running`, this is an interrupted stage. Inspect its existing
   artifacts/history and Git commits; resume the same stage and feature, not a
   second specification. Do not rerun a successful generator or `begin`.
   Ask when evidence is ambiguous; never manually reset the checkpoint.
4. For an active feature, use its recorded branch and directory, except that a
   ready `await_merge` stage starts a progress branch from fetched main
   **before** `begin`. A running `await_merge` resumes its recorded progress
   branch. Re-establish the ignored `.specify/feature.json` with
   `feature_directory` set to that
   recorded path, or set `SPECIFY_FEATURE_DIRECTORY` on each script invocation.
   Never infer feature context from branch names.

## Begin the scheduled stage

Run `python3 scripts/speckit_flow.py begin` **before** calling the stage skill.
For `specify`, also provide `--feature-directory specs/NNN-short-name`; choose
the next available sequential Spec Kit prefix by scanning `specs/`.
The helper pins the first dependency-ready open backlog entry and refuses an
existing directory. Use `feature/NNN-short-name` created from current main.
Constitution uses a `chore/constitution` branch; retain an explicitly designated
appropriate work branch instead when the user requests that.

The `selected.prompt` is read verbatim from the master backlog; do not invent a
summary. Strip only the `/speckit.specify` command prefix when passing its
arguments into the `speckit-specify` skill. Pass the pinned
`SPECIFY_FEATURE_DIRECTORY` explicitly so the generator uses the same path.
`prompt` at the constitution stage similarly comes from its master-doc block.
Invoke the actual existing skill, not just its name in the response. If nested
skill invocation is unsupported, stop and give the exact skill/arguments;
do not claim a stage ran.

| Stage | Execute and gate |
| --- | --- |
| `constitution` | Invoke `speckit-constitution` with the master constitution prompt, charter, architecture, stack, and workflow constraints. Fill governance only. Do not create the first spec. |
| `specify` | Invoke `speckit-specify` with the exact selected backlog prompt and directory. Only one spec. |
| `clarify` | Invoke `speckit-clarify`. Resolve consequential ambiguity; block if user decisions remain. A documented no-question result also counts. |
| `plan` | Invoke `speckit-plan`. Check provider/dependency boundaries, static UI, tests, and constitution. |
| `checklist` | Invoke `speckit-checklist` for relevant requirements-quality domains, explicitly specifying audience/scope. Generate custom checklists but **do not mark them reviewed**. |
| `tasks` | Invoke `speckit-tasks`; preserve requirement/test traceability and dependency ordering. |
| `analyze` | Invoke `speckit-analyze` read-only. Critical/high findings or unresolved coverage/constitution problems block progress. Remediation needs explicit approval outside the analysis skill, then a fresh analysis; don't mutate artifacts inside analysis. |
| `implement` | Invoke `speckit-implement` only after reviewer-owned checklists pass or the reviewer explicitly authorizes proceeding. Never self-approve unchecked custom checklists. Pass the full-stage execution instruction below; complete all remaining tasks and appropriate checks in this invocation unless genuinely blocked. |
| `converge` | Invoke `speckit-converge` after implementation. Appended unchecked tasks send the next invocation back to `implement`; otherwise advance to `finalize`. No automatic endless loop. |
| `finalize` | Verify acceptance evidence, affected docs/README, tests, and architecture review if warranted. Push commits, create/update the feature PR targeting main. Record its number with `finish --pr NUMBER`. |
| `await_merge` | Do not implement more. Verify the recorded PR merged, fetch main/tags, and create a `chore/spec-progress-<id>` branch from main. Invoke `hoard-release` for the derived alpha version at the exact feature merge commit, following the post-merge procedure below. Only after verified publication may the helper record completion and the checkpoint PR become ready. Do not merge it yourself. |

## Full-stage implementation

Pass this instruction with the pinned feature directory to `speckit-implement`:

> Complete every remaining unchecked task in this feature's tasks.md, in
> dependency order, including tests, validation, and documentation. Authorization
> to proceed between tasks, batches, user stories, and phases is implicit.
> Report progress without ending the invocation or asking to continue after a
> successful task/batch. Stop only for a genuine blocker, unresolved question,
> required approval, or explicit user interruption.

This also applies to interrupted implementation and convergence-added tasks.
Follow the installed skill's execution, failure, checklist, and hook rules.
Fix failures within scope when possible; never mark failed or unverified tasks
complete. A phase boundary, validation checkpoint, or commit/push is not a
request for renewed authorization. If the stage skill returns after only a
subset without a blocker, continue its procedure on the remaining tasks in this
same invocation. Do not call `finish` or hand off to another invocation until
all tasks are complete and checks pass, unless reporting an actual blocker.
The one-stage limit still prevents starting `converge` in this invocation.

## Post-merge alpha source release

The maintainer has authorized one source prerelease per spec completed through
this flow. Invoking `await_merge` authorizes pushing that exact derived tag
through `hoard-release`; no extra per-release confirmation is needed. This
authorization does not permit merging PRs, other versions, package publishing,
infrastructure changes, or deployment.

1. Verify the recorded feature PR is merged into fetched `origin/main`, its
   tasks are complete, and acceptance/docs gates still hold. Use its exact
   `mergeCommit.oid`, not an unmerged feature tip or a later main commit.
2. Use `status`'s `release_tag`: `v0.0.X-alpha`, where X is the pinned
   `specs/NNN-short-name` prefix converted to a positive decimal integer.
   `001` becomes `v0.0.1-alpha`, `002` becomes `v0.0.2-alpha`, and `010`
   becomes `v0.0.10-alpha`. Backlog IDs such as F-01 or SPEC-01 do not determine
   the tag. Never silently switch numbering or drop `-alpha`.
3. Invoke the actual `hoard-release` skill with that exact version, merge
   commit, and this standing authorization. Its clean-worktree requirement
   still applies: commit/push the running progress checkpoint before tagging
   and open/update its draft progress PR.
   Observe the `Source release` run and verify the published prerelease,
   generated notes, source archives, and exact tagged commit.
4. On retry, inspect an existing local/remote tag and release first. Reuse only
   an annotated tag at this exact merge commit and a matching published
   prerelease. If only the correct remote tag exists, observe its workflow or
   rerun the specific failed run when appropriate; never retag or silently
   edit a release. Any collision, missing publication, failed run, wrong commit,
   draft, or non-prerelease keeps `await_merge` running and blocks the next spec.
5. Run `finish` with release/run evidence only after publication is verified.
   The helper independently verifies the annotated remote tag and GitHub
   prerelease, then records `release_tag` and `release_url` with completion.
   Commit/push and publish the completion-checkpoint PR. It must merge before
   another invocation starts a new spec.

Previously recorded completions without release metadata remain historical;
do not backfill tags/releases or rewrite their checkpoints without a separate
maintainer request.

## Checkpoint and stop

- After successful execution and gates, run
  `python3 scripts/speckit_flow.py finish --evidence "concise nonsecret result, checks and review references"`.
  Add `--pr NUMBER` at finalize. Artifact existence is only a helper sanity
  check, **not** proof that a quality gate passed; judge the real evidence.
- Do not advance after a failed/blocked stage. Preserve its `running` checkpoint
  and partial work; report the exact blocker. Never use fabricated evidence.
- Commit the checkpoint with its generated/reviewed artifacts, then **push
  immediately**. Each stage is independently durable; don't wait until
  implementation to share progress. Ensure a successful but previously unpushed
  stage is pushed before executing another one.
- Open/update a draft feature PR for incomplete multi-stage work; make it ready
  only after finalize. Constitution and progress-only changes get their own PRs.
  Do not mark a feature complete or unlock its dependencies merely because
  implementation tasks were checked or a PR was opened.
- End with the completed stage, artifact/PR location, next stage, and blockers.
  Include the release URL after successful `await_merge`.
  Stop; the next user invocation authorizes the next stage.
