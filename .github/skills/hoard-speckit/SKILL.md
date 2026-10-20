---
name: hoard-speckit
description: Advance or resume Hoard's dependency-ordered Spec Kit backlog, one checkpointed stage per invocation, beginning with the constitution.
---

# Hoard Spec Kit driver

Use this skill when the user asks to advance/resume the Hoard specification
backlog. **One invocation executes at most one stage.** Do not call this skill
recursively or launch a fleet/workflow engine. This is not permission to build
unrequested features, apply infrastructure, or merge PRs.

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
4. For an active feature, use its recorded branch and directory. Re-establish
   the ignored `.specify/feature.json` with `feature_directory` set to that
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
| `implement` | Invoke `speckit-implement` only after reviewer-owned checklists pass or the reviewer explicitly authorizes proceeding. Never self-approve unchecked custom checklists. Run appropriate checks; unfinished tasks keep this stage running. |
| `converge` | Invoke `speckit-converge` after implementation. Appended unchecked tasks send the next invocation back to `implement`; otherwise advance to `finalize`. No automatic endless loop. |
| `finalize` | Verify acceptance evidence, affected docs/README, tests, and architecture review if warranted. Push commits, create/update the feature PR targeting main. Record its number with `finish --pr NUMBER`. |
| `await_merge` | Do not implement more. Verify the recorded PR merged, fetch main, and create a `chore/spec-progress-<id>` branch from main. The helper verifies merge ancestry and records completion; publish the checkpoint PR. Do not merge it yourself. |

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
  Stop; the next user invocation authorizes the next stage.
