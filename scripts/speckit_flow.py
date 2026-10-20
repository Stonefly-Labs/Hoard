#!/usr/bin/env python3
"""Persist Hoard's one-stage-at-a-time Spec Kit workflow; never run an AI stage."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(".specify/hoard-flow.json")
BACKLOG = Path("docs/HOARD_SPECKIT_MASTER_BACKLOG.md")
STAGES = (
    "constitution", "specify", "clarify", "plan", "checklist", "tasks",
    "analyze", "implement", "converge", "finalize", "await_merge",
)
BRANCH = re.compile(r"^[a-z][a-z0-9-]*/[a-z0-9][a-z0-9._/-]*$")


def command(root, *args):
    return subprocess.run(
        args, cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_branch(root):
    branch = command(root, "git", "branch", "--show-current")
    if not BRANCH.fullmatch(branch):
        raise ValueError("Use a type-prefixed work branch, never main or a detached HEAD.")
    return branch


def load_state(root):
    state = json.loads((root / STATE).read_text())
    if (
        not isinstance(state, dict)
        or not {"schema_version", "stage", "status", "branch", "active", "completed", "history"} <= state.keys()
        or state.get("schema_version") != 1
        or state.get("stage") not in STAGES
        or state.get("status") not in ("ready", "running")
        or not isinstance(state.get("completed"), list)
        or not isinstance(state.get("history"), list)
    ):
        raise ValueError("Invalid flow checkpoint; restore/reconcile it from Git, do not reset it.")
    active = state["active"]
    if active is not None:
        if (
            not isinstance(active, dict)
            or not {"id", "feature_directory", "pr"} <= active.keys()
            or not isinstance(active["id"], str)
            or not isinstance(active["feature_directory"], str)
        ):
            raise ValueError("Invalid active feature in checkpoint.")
        feature_path(root, active["feature_directory"])
    elif state["stage"] not in ("constitution", "specify"):
        raise ValueError("Current stage requires a pinned active feature.")
    if state["status"] == "running" and not state["branch"]:
        raise ValueError("Running checkpoint is missing its work branch.")
    if state["stage"] == "await_merge" and not isinstance(active["pr"], int):
        raise ValueError("Merge gate is missing its feature PR number.")
    if any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in state["completed"]):
        raise ValueError("Invalid completed-spec records.")
    if len({item["id"] for item in state["completed"]}) != len(state["completed"]):
        raise ValueError("Duplicate completed-spec records.")
    return state


def save_state(root, state):
    path = root / STATE
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(path)


def dependencies(value):
    result = []
    if value == "None":
        return result
    for token in value.split(","):
        token = token.strip()
        span = re.fullmatch(r"(F-)?(\d{2})[–-](?:F-)?(\d{2})", token)
        if span:
            prefix, start, end = span.groups()
            if int(start) > int(end):
                raise ValueError(f"Invalid dependency range: {token}")
            result.extend(f"{prefix or ''}{number:02}" for number in range(int(start), int(end) + 1))
        elif re.fullmatch(r"(?:F-)?\d{2}", token):
            result.append(token)
        else:
            raise ValueError(f"Unrecognized dependency: {token}")
    return result


def load_backlog(root):
    text = (root / BACKLOG).read_text()
    entries = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4 or not re.fullmatch(r"(?:F-)?\d{2}", cells[0]):
            continue
        entries.append({
            "id": cells[0],
            "title": cells[2],
            "dependencies": dependencies(cells[3]),
        })
    if not entries or len({item["id"] for item in entries}) != len(entries):
        raise ValueError("Backlog inventory is missing or has duplicate IDs.")
    ids = {item["id"] for item in entries}
    for item in entries:
        unknown = set(item["dependencies"]) - ids
        if unknown:
            raise ValueError(f"Unknown dependencies for {item['id']}: {sorted(unknown)}")
        heading_id = item["id"] if item["id"].startswith("F-") else f"SPEC-{item['id']}"
        section = re.search(
            rf"^### {re.escape(heading_id)}:.*?\n(.*?)(?=^### |\Z)",
            text, re.MULTILINE | re.DOTALL,
        )
        prompt = re.search(r"```text\s*\n(/speckit\.specify .*?)\n```", section[1], re.DOTALL) if section else None
        if not prompt:
            raise ValueError(f"Missing specify prompt for {item['id']}.")
        item["prompt"] = prompt[1]
    return entries


def select_spec(entries, completed):
    done = {item["id"] for item in completed}
    unknown = done - {item["id"] for item in entries}
    if unknown:
        raise ValueError(f"Completed IDs missing from backlog: {sorted(unknown)}")
    remaining = [item for item in entries if item["id"] not in done]
    for item in remaining:
        if set(item["dependencies"]) <= done:
            return item
    if remaining:
        raise ValueError("Open specs have unmet/cyclic dependencies; reconcile the backlog.")
    return None


def status(root, state):
    entries = load_backlog(root)
    selected = (
        next((item for item in entries if item["id"] == state["active"]["id"]), None)
        if state["active"] else select_spec(entries, state["completed"])
    )
    if state["active"] and not selected:
        raise ValueError("Active spec no longer exists in the backlog.")
    result = dict(state, selected=selected)
    if state["stage"] == "constitution":
        text = (root / BACKLOG).read_text()
        prompt = re.search(r"```text\s*\n(/speckit\.constitution .*?)\n```", text, re.DOTALL)
        if not prompt:
            raise ValueError("Missing constitution prompt in master backlog.")
        result["prompt"] = prompt[1]
    return result


def feature_path(root, value):
    path = Path(value)
    resolved = (root / path).resolve()
    specs = (root / "specs").resolve()
    if path.is_absolute() or len(path.parts) != 2 or path.parts[0] != "specs" or not resolved.is_relative_to(specs):
        raise ValueError("Feature directory must be one repository-relative specs/<feature> directory.")
    if not re.fullmatch(r"\d{3,}-[a-z0-9-]+", path.name):
        raise ValueError("Feature directory must use Spec Kit's sequential NNN-short-name format.")
    return path.as_posix()


def begin(root, state, directory=None):
    if state["status"] == "running":
        raise ValueError("Stage already running: reconcile its artifacts, then finish; do not rerun begin.")
    branch = git_branch(root)
    if state["branch"] and state["branch"] != branch and state["stage"] != "await_merge":
        raise ValueError(f"Resume on {state['branch']}, not {branch}.")
    if state["stage"] == "specify":
        selected = select_spec(load_backlog(root), state["completed"])
        if selected is None:
            raise ValueError("All backlog specs are complete; no new feature to start.")
        if not directory:
            raise ValueError("specify requires --feature-directory specs/NNN-short-name.")
        directory = feature_path(root, directory)
        if (root / directory).exists():
            raise ValueError("Feature directory already exists; reconcile instead of duplicating a spec.")
        state["active"] = {"id": selected["id"], "feature_directory": directory, "pr": None}
    state.update(status="running", branch=branch)
    save_state(root, state)
    return state


def require_artifact(root, relative):
    path = root / relative
    if not path.is_file() or not path.read_text().strip():
        raise ValueError(f"Required nonempty artifact is missing: {relative}")
    return path.read_text()


def unfinished_tasks(root, directory):
    text = require_artifact(root, f"{directory}/tasks.md")
    if not re.search(r"^- \[[xX ]\] T\d+", text, re.MULTILINE):
        raise ValueError("tasks.md contains no Spec Kit tasks.")
    return bool(re.search(r"^- \[ \] T\d+", text, re.MULTILINE))


def pull_request(root, number):
    return json.loads(command(
        root, "gh", "pr", "view", str(number),
        "--json", "number,state,headRefName,baseRefName,mergeCommit",
    ))


def finish(root, state, evidence, pr_number=None):
    if state["status"] != "running":
        raise ValueError("Run begin before executing/finishing a stage.")
    branch = git_branch(root)
    if state["branch"] != branch:
        raise ValueError(f"Stage started on {state['branch']}; do not checkpoint on {branch}.")
    if not evidence.strip():
        raise ValueError("Supply nonempty, nonsecret stage evidence.")
    stage = state["stage"]
    directory = state["active"]["feature_directory"] if state["active"] else None
    next_stage = STAGES[STAGES.index(stage) + 1] if stage != "await_merge" else "specify"
    if stage == "constitution":
        text = require_artifact(root, ".specify/memory/constitution.md")
        if re.search(r"\[[A-Z][A-Z0-9_ ]+\]", text):
            raise ValueError("Constitution still contains template placeholders.")
    elif stage in ("specify", "clarify"):
        text = require_artifact(root, f"{directory}/spec.md")
        if stage == "clarify" and "NEEDS CLARIFICATION" in text:
            raise ValueError("Resolve remaining specification clarifications before planning.")
    elif stage == "plan":
        require_artifact(root, f"{directory}/plan.md")
    elif stage == "checklist":
        checklists = list((root / directory / "checklists").glob("*.md"))
        if not any(path.name != "requirements.md" and path.read_text().strip() for path in checklists):
            raise ValueError("Generate at least one custom requirements-quality checklist.")
    elif stage in ("tasks", "analyze", "implement", "converge", "finalize"):
        remaining = unfinished_tasks(root, directory)
        if stage in ("implement", "finalize") and remaining:
            raise ValueError("Implementation still has unchecked tasks; keep the current stage.")
        if stage == "converge" and remaining:
            next_stage = "implement"
        if stage == "finalize":
            if not pr_number:
                raise ValueError("finalize requires --pr with the open PR number.")
            pr = pull_request(root, pr_number)
            if pr["state"] != "OPEN" or pr["headRefName"] != branch or pr["baseRefName"] != "main":
                raise ValueError("PR must be open from this feature branch to main.")
            state["active"]["pr"] = pr_number
    elif stage == "await_merge":
        pr = pull_request(root, state["active"]["pr"])
        if pr["state"] != "MERGED" or not pr["mergeCommit"]:
            raise ValueError("Feature PR is not merged; do not complete the backlog entry.")
        merge_commit = pr["mergeCommit"]["oid"]
        command(root, "git", "merge-base", "--is-ancestor", merge_commit, "origin/main")
        if unfinished_tasks(root, directory):
            raise ValueError("Merged feature still has unchecked tasks.")
        state["completed"].append(dict(state["active"], merge_commit=merge_commit))
    state["history"].append({
        "stage": stage,
        "spec_id": state["active"]["id"] if state["active"] else None,
        "branch": branch,
        "at": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence.strip(),
    })
    if stage == "await_merge":
        state["active"] = None
    state.update(stage=next_stage, status="ready")
    if stage in ("constitution", "await_merge"):
        state["branch"] = None
    save_state(root, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    start = sub.add_parser("begin")
    start.add_argument("--feature-directory")
    complete = sub.add_parser("finish")
    complete.add_argument("--evidence", required=True)
    complete.add_argument("--pr", type=int)
    args = parser.parse_args()
    try:
        state = load_state(ROOT)
        if args.action == "begin":
            begin(ROOT, state, args.feature_directory)
        elif args.action == "finish":
            finish(ROOT, state, args.evidence, args.pr)
        print(json.dumps(status(ROOT, state), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.strip() or f"Git/GitHub prerequisite failed (exit {error.returncode}): {error.cmd}"
        else:
            detail = str(error)
        print(f"Flow blocked: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
