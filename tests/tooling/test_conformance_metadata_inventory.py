import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import conformance_unit_checks as checks


class MetadataInventoryControllerTests(unittest.TestCase):
    def test_unchanged_complete_suite_exposes_named_assertion_then_same_source_repair(self):
        root = Path(__file__).resolve().parents[2]
        original = (root / "scripts/metadata_evidence.py").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve() / "metadata_evidence.py"
            with patch.object(unittest.defaultTestLoader, "testNamePatterns", ["*foreign-filter*"]):
                rows = [checks.metadata_inventory(root, mode, source)
                        for mode in ("baseline", "mutation", "repair")]
            self.assertEqual([0, 1, 0], [row["exitCode"] for row in rows])
            self.assertEqual([17, 17, 17], [row["tests"] for row in rows])
            self.assertEqual([0, 0, 0], [row["errors"] for row in rows])
            self.assertEqual([0, 0, 0], [row["skipped"] for row in rows])
            self.assertEqual([0, 1, 0], [row["failures"] for row in rows])
            self.assertEqual([[], [checks.METADATA_INVENTORY_FAILURE], []],
                             [row["failedTests"] for row in rows])
            self.assertEqual(1, len({row["suiteSha256"] for row in rows}))
            self.assertEqual(1, len({row["testsSha256"] for row in rows}))
            self.assertEqual(hashlib.sha256(original).hexdigest(), rows[0]["executedSha256"])
            self.assertNotEqual(rows[0]["executedSha256"], rows[1]["executedSha256"])
            self.assertEqual(rows[0]["executedSha256"], rows[2]["executedSha256"])
            self.assertEqual(original, source.read_bytes())
            self.assertEqual(original, (root / "scripts/metadata_evidence.py").read_bytes())

    def test_missing_reordered_and_changed_adapter_state_rejects(self):
        root = Path(__file__).resolve().parents[2]
        from conformance_evidence import ConformanceError
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve() / "metadata_evidence.py"
            with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
                checks.metadata_inventory(root, "mutation", source)
            checks.metadata_inventory(root, "baseline", source)
            with self.assertRaisesRegex(ConformanceError, "ProofMismatch"):
                checks.metadata_inventory(root, "repair", source)
            source.write_text("private-canary")
            with self.assertRaisesRegex(ConformanceError, "ProofMismatch"):
                checks.metadata_inventory(root, "mutation", source)
            with self.assertRaisesRegex(ConformanceError, "EvidenceSchemaInvalid"):
                checks.metadata_inventory(root, "other", source)


if __name__ == "__main__":
    unittest.main()
