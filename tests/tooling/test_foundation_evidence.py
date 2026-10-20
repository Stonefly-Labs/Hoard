import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import foundation_evidence as foundation


class AcceptanceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def archive(self, name, stamp, identifier, package_id="Hoard.Fixtures.Test", signed=False):
        path = self.root / name
        metadata = f"package/services/metadata/core-properties/{identifier}.psmdcp"
        entries = {
            f"{package_id}.nuspec": f"<package><metadata><id>{package_id}</id><version>0.1.0</version></metadata></package>".encode(),
            "lib/net10.0/Fixture.dll": b"unchanged assembly payload",
            "[Content_Types].xml": b"unchanged content types",
            metadata: b"unchanged OPC core properties",
            "_rels/.rels": (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Type="manifest" Target="/{package_id}.nuspec" Id="{identifier}a" />'
                f'<Relationship Type="metadata" Target="/{metadata}" Id="{identifier}b" />'
                '</Relationships>').encode(),
        }
        if signed:
            entries[".signature.p7s"] = b"must not rewrite signed inputs"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries.items():
                archive.writestr(zipfile.ZipInfo(name, stamp), content)
        return path

    def test_only_envelope_changes_and_distinct_pack_runs_replay_identically(self):
        first = self.archive("first.nupkg", (2026, 1, 1, 1, 1, 0), "first")
        second = self.archive("second.nupkg", (2026, 2, 2, 2, 2, 0), "second")
        with zipfile.ZipFile(first) as original:
            payloads = {name: original.read(name) for name in original.namelist()
                        if name != "_rels/.rels" and not name.endswith(".psmdcp")}
        for path in (first, second):
            foundation.canonicalize_acceptance_archive(path)
            with zipfile.ZipFile(path) as archive:
                for name, content in payloads.items():
                    self.assertEqual(archive.read(name), content)
                metadata = next(n for n in archive.namelist() if n.endswith(".psmdcp"))
                self.assertEqual(archive.read(metadata), b"unchanged OPC core properties")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_signed_or_nonlocal_packages_are_rejected_without_rewriting(self):
        for path in (
                self.archive("signed.nupkg", (2026, 1, 1, 0, 0, 0), "signed", signed=True),
                self.archive("external.nupkg", (2026, 1, 1, 0, 0, 0), "external", package_id="External.Test")):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "unsigned local Hoard"):
                    foundation.canonicalize_acceptance_archive(path)
                self.assertEqual(path.read_bytes(), original)

    def test_incomplete_opc_inputs_fail_explicitly(self):
        path = self.root / "incomplete.nupkg"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Hoard.Fixtures.Test.nuspec",
                             "<package><metadata><id>Hoard.Fixtures.Test</id></metadata></package>")
        original = path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "OPC"):
            foundation.canonicalize_acceptance_archive(path)
        self.assertEqual(path.read_bytes(), original)
