import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.artifacts import (
    INVENTORY,
    ROOT,
    allowed_managed_path,
    digest,
    read_inventory,
    stage_source,
    synchronize,
)


class ArtifactContractTests(unittest.TestCase):
    def test_source_frontmatter_and_names(self):
        sources = ROOT / ".apm"
        for path in sources.rglob("*.md"):
            if "references" in path.parts:
                continue
            with self.subTest(path=path):
                text = path.read_text()
                self.assertTrue(text.isascii())
                self.assertTrue(text.startswith("---\n"))
                frontmatter, body = text[4:].split("\n---\n", 1)
                self.assertTrue(body.strip())
                if path.name.endswith(".instructions.md"):
                    self.assertRegex(frontmatter, r'applyTo: ".+"')
                else:
                    self.assertRegex(frontmatter, r"(?m)^description: .+$")
                if path.name == "SKILL.md":
                    self.assertIn(f"name: {path.parent.name}", frontmatter)
                else:
                    self.assertTrue(path.name.startswith("saba-"))
                # APM parses full YAML during the real install/consumer check.
                self.assertNotRegex(frontmatter, r"(?m)^(mcp-servers|hooks):")

    def test_agent_permissions_are_explicit(self):
        for name in ("designer", "reviewer"):
            text = (ROOT / f".apm/agents/saba-api-{name}.agent.md").read_text()
            self.assertIn("tools: [read, search]", text)
        text = (ROOT / ".apm/agents/saba-api-builder.agent.md").read_text()
        self.assertIn("tools: [read, search, edit, execute]", text)

    def test_packaged_relative_links_resolve(self):
        for directory in (ROOT / ".apm/skills", ROOT / ".agents/skills"):
            for path in directory.rglob("*.md"):
                for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    if "://" in link or link.startswith("#"):
                        continue
                    target = (path.parent / link.split("#")[0]).resolve()
                    with self.subTest(path=path, link=link):
                        self.assertTrue(target.is_relative_to(directory.resolve()))
                        self.assertTrue(target.is_file())

    def test_requirement_ids_are_unique_and_reviewable(self):
        definitions = []
        for path in (ROOT / ".apm/instructions").glob("*.md"):
            definitions.extend(re.findall(r"\*\*(SABA-[A-Z]+-\d{3}):\*\*", path.read_text()))
        self.assertEqual(len(definitions), len(set(definitions)))
        self.assertGreater(len(definitions), 0)
        matrix = (ROOT / ".apm/skills/saba-verify-api/references/verification-matrix.md").read_text()
        standards = (ROOT / "docs/standards.md").read_text()
        for requirement in definitions:
            self.assertIn(requirement, matrix)
            self.assertIn(requirement, standards)

    def test_export_contains_only_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "source"
            stage_source(output)
            self.assertEqual({p.name for p in output.iterdir()}, {"apm.yml", ".apm"})
            self.assertFalse(list(output.rglob("*.py")))
            self.assertFalse(list(output.rglob("*.pem")))


class ProjectionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.stage = self.root / "stage"
        self.destination = self.root / "consumer"
        self.file = ".github/agents/saba-example.agent.md"
        (self.stage / self.file).parent.mkdir(parents=True)
        (self.stage / self.file).write_text("---\ndescription: Example\n---\nExample\n")
        (self.stage / "apm.lock.yaml").write_text("lockfile_version: '1'\n")
        self.destination.mkdir()

    def test_sync_is_idempotent_and_preserves_unrelated_files(self):
        unrelated = self.destination / ".github/agents/team-agent.agent.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("Team-owned content\n")
        synchronize(self.stage, self.destination, write=True)
        initial = (self.destination / INVENTORY).read_bytes()
        synchronize(self.stage, self.destination, write=True)
        synchronize(self.stage, self.destination, write=False)
        self.assertEqual((self.destination / INVENTORY).read_bytes(), initial)
        self.assertEqual(unrelated.read_text(), "Team-owned content\n")

    def test_tampering_fails_before_regeneration(self):
        synchronize(self.stage, self.destination, write=True)
        altered = self.destination / self.file
        altered.write_text("Unreviewed local edit\n")
        with self.assertRaisesRegex(RuntimeError, "Managed file changed"):
            synchronize(self.stage, self.destination, write=True)
        self.assertEqual(altered.read_text(), "Unreviewed local edit\n")

    def test_source_change_requires_refresh(self):
        synchronize(self.stage, self.destination, write=True)
        (self.stage / self.file).write_text("Approved source change\n")
        with self.assertRaisesRegex(RuntimeError, "Canonical artifacts changed"):
            synchronize(self.stage, self.destination, write=False)
        synchronize(self.stage, self.destination, write=True)
        self.assertEqual((self.destination / self.file).read_text(), "Approved source change\n")

    def test_unmanaged_collision_is_not_overwritten(self):
        (self.destination / self.file).parent.mkdir(parents=True)
        (self.destination / self.file).write_text("Existing file\n")
        with self.assertRaisesRegex(RuntimeError, "Unmanaged file collision"):
            synchronize(self.stage, self.destination, write=True)

    def test_removed_source_only_removes_unchanged_managed_file(self):
        synchronize(self.stage, self.destination, write=True)
        (self.stage / self.file).unlink()
        synchronize(self.stage, self.destination, write=True)
        self.assertFalse((self.destination / self.file).exists())

    def test_inventory_rejects_unsafe_paths(self):
        for name in ("../../secret", "/tmp/outside", ".github/workflows/ci.yml", ".github/agents/x"):
            self.assertFalse(allowed_managed_path(name))
        (self.destination / INVENTORY).parent.mkdir(parents=True)
        (self.destination / INVENTORY).write_text(json.dumps({
            "format": 1, "files": {"../../secret": "a" * 64},
        }))
        with self.assertRaisesRegex(RuntimeError, "Unsafe"):
            read_inventory(self.destination)

    def test_symlinked_parent_is_not_followed(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.destination / ".github").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "Symlinked"):
            synchronize(self.stage, self.destination, write=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_inventory_records_actual_bytes(self):
        synchronize(self.stage, self.destination, write=True)
        inventory = read_inventory(self.destination)
        self.assertEqual(inventory[self.file], digest(self.destination / self.file))


if __name__ == "__main__":
    unittest.main()
