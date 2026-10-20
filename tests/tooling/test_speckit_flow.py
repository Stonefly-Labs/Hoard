import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import speckit_flow as flow


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative in (flow.BACKLOG,):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(flow.ROOT / relative, destination)
        self.state = {
            "schema_version": 1, "stage": "constitution", "status": "ready",
            "branch": None, "active": None, "completed": [], "history": [],
        }
        self.write(flow.STATE, json.dumps(self.state))
        self.write(".specify/memory/constitution.md", "# [PROJECT_NAME] Constitution\n[PRINCIPLE_1_NAME]\n")
        self.branch = patch.object(flow, "git_branch", return_value="feature/001-contracts")
        self.branch.start()
        self.addCleanup(self.branch.stop)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def active(self, stage, tasks="- [x] T001 Implement contracts\n"):
        self.state.update(
            stage=stage, status="running", branch="feature/001-contracts",
            active={"id": "F-01", "feature_directory": "specs/001-contracts", "pr": None},
        )
        self.write("specs/001-contracts/tasks.md", tasks)

    def test_real_backlog_range_and_dependency_aware_selection(self):
        entries = flow.load_backlog(self.root)
        self.assertEqual(flow.select_spec(entries, [])["id"], "F-01")
        foundation = [{"id": f"F-{number:02}"} for number in range(1, 8)]
        self.assertEqual(flow.select_spec(entries, foundation)["id"], "01")
        self.assertEqual(
            next(item for item in entries if item["id"] == "F-07")["dependencies"],
            [f"F-{number:02}" for number in range(1, 7)],
        )
        selected = flow.select_spec(entries, [])
        self.assertIn(selected["prompt"], (self.root / flow.BACKLOG).read_text())

    def test_status_is_read_only_and_constitution_remains_first(self):
        original = (self.root / flow.STATE).read_bytes()
        result = flow.status(self.root, self.state)
        self.assertEqual(result["stage"], "constitution")
        self.assertTrue(result["prompt"].startswith("/speckit.constitution "))
        self.assertEqual((self.root / flow.STATE).read_bytes(), original)
        self.assertFalse((self.root / ".specify/feature.json").exists())

    def test_constitution_template_blocks_then_checkpoints_only_one_stage(self):
        flow.begin(self.root, self.state)
        with self.assertRaisesRegex(ValueError, "placeholders"):
            flow.finish(self.root, self.state, "Not ratified")
        self.assertEqual(flow.load_state(self.root)["status"], "running")
        self.write(".specify/memory/constitution.md", "# Hoard Constitution\nRatified governance.\n")
        flow.finish(self.root, self.state, "Governance reviewed")
        resumed = flow.load_state(self.root)
        self.assertEqual(resumed["stage"], "specify")
        self.assertEqual(len(resumed["history"]), 1)
        self.assertIsNone(resumed["active"])

    def test_interrupted_specify_pins_feature_and_refuses_duplicate_begin(self):
        self.state["stage"] = "specify"
        flow.begin(self.root, self.state, "specs/001-contracts")
        with self.assertRaisesRegex(ValueError, "already running"):
            flow.begin(self.root, flow.load_state(self.root), "specs/002-duplicate")
        resumed = flow.load_state(self.root)
        self.assertEqual(resumed["active"]["id"], "F-01")
        self.assertEqual(resumed["active"]["feature_directory"], "specs/001-contracts")
        self.write("specs/001-contracts/spec.md", "# Provider contracts\n")
        flow.finish(self.root, resumed, "Specification reviewed")
        self.assertEqual(flow.load_state(self.root)["stage"], "clarify")

    def test_directory_escape_and_existing_directory_are_rejected(self):
        self.state["stage"] = "specify"
        for directory in ("../outside", "/tmp/specs/001-test", "specs/../escape", "specs/not-numbered"):
            with self.subTest(directory=directory), self.assertRaises(ValueError):
                flow.begin(self.root, self.state, directory)
        (self.root / "specs/001-existing").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "already exists"):
            flow.begin(self.root, self.state, "specs/001-existing")

    def test_wrong_branch_or_unresolved_clarification_cannot_advance(self):
        self.active("clarify")
        self.write("specs/001-contracts/spec.md", "[NEEDS CLARIFICATION: identity]\n")
        with self.assertRaisesRegex(ValueError, "clarifications"):
            flow.finish(self.root, self.state, "Still blocked")
        with patch.object(flow, "git_branch", return_value="bugfix/other"):
            with self.assertRaisesRegex(ValueError, "do not checkpoint"):
                flow.finish(self.root, self.state, "Wrong branch")

    def test_main_and_detached_head_are_not_work_branches(self):
        self.branch.stop()
        for branch in ("main", "", "unprefixed"):
            with self.subTest(branch=branch), patch.object(flow, "command", return_value=branch):
                with self.assertRaisesRegex(ValueError, "work branch"):
                    flow.git_branch(self.root)

    def test_unfinished_implementation_blocks_and_convergence_returns_to_implement(self):
        self.active("implement", "- [ ] T001 Implement contracts\n")
        with self.assertRaisesRegex(ValueError, "unchecked tasks"):
            flow.finish(self.root, self.state, "Incomplete")
        self.state["stage"] = "converge"
        flow.finish(self.root, self.state, "Convergence appended gap T001")
        self.assertEqual(self.state["stage"], "implement")
        self.state["stage"] = "converge"
        self.state["status"] = "running"
        self.write("specs/001-contracts/tasks.md", "- [x] T001 Implement contracts\n")
        flow.finish(self.root, self.state, "All acceptance gaps closed")
        self.assertEqual(self.state["stage"], "finalize")

    def test_finalize_requires_actual_feature_pr_and_does_not_complete_spec(self):
        self.active("finalize")
        with patch.object(flow, "pull_request", return_value={
            "state": "OPEN", "headRefName": "feature/other", "baseRefName": "main",
        }):
            with self.assertRaisesRegex(ValueError, "this feature branch"):
                flow.finish(self.root, self.state, "Wrong PR", 42)
        with patch.object(flow, "pull_request", return_value={
            "state": "OPEN", "headRefName": "feature/001-contracts", "baseRefName": "main",
        }):
            flow.finish(self.root, self.state, "Acceptance and docs verified", 42)
        self.assertEqual(self.state["stage"], "await_merge")
        self.assertEqual(self.state["active"]["pr"], 42)
        self.assertEqual(self.state["completed"], [])

    def test_completion_requires_merge_and_origin_main_ancestry(self):
        self.active("await_merge")
        self.state["active"]["pr"] = 42
        with patch.object(flow, "pull_request", return_value={"state": "OPEN", "mergeCommit": None}):
            with self.assertRaisesRegex(ValueError, "not merged"):
                flow.finish(self.root, self.state, "Still open")
        self.assertEqual(self.state["completed"], [])
        with patch.object(flow, "pull_request", return_value={
            "state": "MERGED", "mergeCommit": {"oid": "abc123"},
        }), patch.object(flow, "command") as command:
            flow.finish(self.root, self.state, "Merged PR #42, acceptance verified")
        command.assert_called_once_with(
            self.root, "git", "merge-base", "--is-ancestor", "abc123", "origin/main",
        )
        self.assertEqual(self.state["stage"], "specify")
        self.assertEqual(self.state["completed"][0]["id"], "F-01")
        self.assertIsNone(self.state["active"])

    def test_corrupt_checkpoint_and_unknown_dependencies_fail_explicitly(self):
        self.write(flow.STATE, json.dumps({"schema_version": 1, "stage": "plan"}))
        with self.assertRaisesRegex(ValueError, "Invalid flow checkpoint"):
            flow.load_state(self.root)
        backlog = (self.root / flow.BACKLOG).read_text().replace("| F-01 | P0 |", "| F-99 | P0 |", 1)
        self.write(flow.BACKLOG, backlog)
        with self.assertRaises(ValueError):
            flow.load_backlog(self.root)


if __name__ == "__main__":
    unittest.main()
