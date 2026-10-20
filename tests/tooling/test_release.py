import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import release


class ReleaseTests(unittest.TestCase):
    def test_stable_and_prerelease_classification(self):
        self.assertEqual(release.metadata("v1.2.3")["prerelease"], "false")
        for tag in ("v0.1.0-alpha.1", "v1.0.0-rc.0", "v2.0.0-preview-1"):
            with self.subTest(tag=tag):
                self.assertEqual(release.metadata(tag)["prerelease"], "true")

    def test_invalid_tags_are_rejected(self):
        for tag in (
            "1.2.3", "v1.2", "v01.2.3", "v1.2.3-01", "v1.2.3-rc.01",
            "v1.2.3+build", "v1.2.3-", "v1.2.3\n", "v1.2.3;echo unsafe",
            "v1.2.3-rc..1", "v１.2.3",
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.metadata(tag)

    def test_main_ancestry_accepts_merged_source_and_rejects_feature_tag(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True,
                    capture_output=True, text=True,
                ).stdout.strip()

            git("init", "-b", "main")
            git("-c", "user.name=Tooling Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "Initial reviewed source")
            main = git("rev-parse", "HEAD")
            git("update-ref", "refs/remotes/origin/main", main)
            git("tag", "v0.1.0", main)
            self.assertEqual(release.check_main(root, "v0.1.0"), main)
            git("switch", "-c", "feature/unmerged")
            git("-c", "user.name=Tooling Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "Unmerged change")
            git("tag", "v0.2.0")
            with self.assertRaises(subprocess.CalledProcessError):
                release.check_main(root, "v0.2.0")
            with self.assertRaises(subprocess.CalledProcessError):
                release.check_main(root, "v9.9.9")


if __name__ == "__main__":
    unittest.main()
