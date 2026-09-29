"""Filesystem and CLI tests for the read-only skill inventory."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scan_skills.py"
SPEC = importlib.util.spec_from_file_location("scan_skills", SCRIPT)
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)


class SkillScanTests(unittest.TestCase):
    """Exercise discovery, metadata, aliases, exclusions and partial failure."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-scan-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def skill(self, relative, name=None, frontmatter=None):
        """Create a minimal library fixture without touching real projects."""
        directory = self.root / relative
        directory.mkdir(parents=True, exist_ok=True)
        name = name or directory.name
        header = frontmatter or f"name: {name}\ndescription: Use this library for archives."
        manifest = directory / "SKILL.md"
        manifest.write_text(f"---\n{header}\n---\n\n# Usage\n", encoding="utf-8")
        return manifest

    def link(self, relative, target):
        """Create a project-relative registration link, including broken ones."""
        link = self.root / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
        return link

    def scan(self, *extra):
        scanner = SCAN.Scanner()
        for root in (self.root,) + extra:
            scanner.scan_root(root)
        return scanner.result()

    def test_unregistered_library_and_standard_entries(self):
        source = self.skill("packages/archive/skills/archive-tool")
        self.skill(".agents/skills/registered-tool")
        report = self.scan()
        self.assertTrue(report["scan_complete"])
        self.assertEqual(len(report["skills"]), 2)
        first = report["skills"][0]
        self.assertEqual(first["skill_path"], str(source))
        self.assertEqual(first["discovery_entries"], [])
        self.assertEqual(report["skills"][1]["discovery_entries"][0]["host"], "codex")

    def test_two_hosts_deduplicate_one_source(self):
        source = self.skill("packages/archive/skills/archive-tool")
        self.link(".agents/skills/archive-tool", source.parent)
        self.link(".claude/skills/archive-tool", source.parent)
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        report = self.scan()
        self.assertTrue(report["scan_complete"])
        self.assertEqual(len(report["skills"]), 1)
        record = report["skills"][0]
        self.assertEqual(len(record["paths"]), 3)
        self.assertEqual({e["host"] for e in record["discovery_entries"]}, {"codex", "claude-code"})
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))
        self.assertEqual(report, self.scan())

    def test_library_excluded_by_default_can_be_explicitly_scanned(self):
        self.skill("node_modules/archive/skills/archive-tool")
        self.skill("dist/not-a-real-tool")
        self.assertEqual(self.scan()["skills"], [])
        report = self.scan(self.root / "node_modules/archive")
        self.assertEqual([s["name"] for s in report["skills"]], ["archive-tool"])

    def test_additional_exclusion(self):
        self.skill("generated/archive-tool")
        scanner = SCAN.Scanner(["generated"])
        scanner.scan_root(self.root)
        self.assertEqual(scanner.result()["skills"], [])

    def test_multiline_yaml_and_host_extensions(self):
        self.skill("skills/archive-tool", frontmatter="""name: archive-tool
description: >-
  Archive files safely:
  read and write bundles.
when_to_use: |
  用户需要创建归档时。
argument-hint: '[path]'
effort: high
metadata:
  custom: 'kept in source'
""")
        report = self.scan()
        self.assertTrue(report["scan_complete"])
        record = report["skills"][0]
        self.assertEqual(record["description"], "Archive files safely: read and write bundles.")
        self.assertEqual(record["when_to_use"], "用户需要创建归档时。")

    def test_bad_yaml_does_not_hide_other_skills(self):
        self.skill("skills/bad-tool", frontmatter="name: [unterminated")
        self.skill("skills/good-tool")
        report = self.scan()
        self.assertFalse(report["scan_complete"])
        self.assertEqual([s["name"] for s in report["skills"]], ["good-tool"])
        self.assertEqual(report["diagnostics"][0]["code"], "frontmatter_invalid")

    def test_broken_link_and_link_loop_are_diagnostics(self):
        self.link(".agents/skills/missing", self.root / "gone")
        self.link(".claude/skills/loop", self.root / ".claude/skills/loop")
        report = self.scan()
        self.assertFalse(report["scan_complete"])
        self.assertEqual(len(report["diagnostics"]), 2)

    def test_arbitrary_directory_symlink_is_not_followed(self):
        self.skill("node_modules/archive/skills/archive-tool")
        self.link("linked-package", self.root / "node_modules/archive")
        report = self.scan()
        self.assertEqual(report["skills"], [])
        self.assertIn(str(self.root / "linked-package"), report["skipped_symlink_directories"])
        explicit = self.scan(self.root / "linked-package")
        self.assertEqual(len(explicit["skills"]), 1)

    def test_linked_host_skills_root(self):
        source = self.skill("node_modules/catalog/archive-tool")
        self.link(".agents/skills", source.parent.parent)
        report = self.scan()
        self.assertTrue(report["scan_complete"])
        self.assertEqual(len(report["skills"]), 1)
        self.assertEqual(report["skills"][0]["discovery_entries"][0]["host"], "codex")

    def test_duplicate_names_remain_distinct(self):
        self.skill("packages/a/skills/same-tool")
        self.skill("packages/b/skills/same-tool")
        report = self.scan()
        self.assertEqual(len(report["skills"]), 2)
        self.assertEqual(len(report["same_name_skills"]), 1)
        self.assertEqual(len(report["same_name_skills"][0]["skill_paths"]), 2)

    def test_invalid_required_metadata_is_visible(self):
        for directory, header in [
            ("a", "name: INVALID\ndescription: test"),
            ("b", "name: b\ndescription: false"),
            ("c", "- not-a-mapping"),
        ]:
            self.skill("skills/" + directory, frontmatter=header)
        report = self.scan()
        self.assertFalse(report["scan_complete"])
        self.assertEqual(len(report["diagnostics"]), 3)

    def test_mismatched_source_name_is_not_silently_valid(self):
        self.skill("skills/directory-name", name="different-name")
        report = self.scan()
        self.assertFalse(report["scan_complete"])
        self.assertEqual(report["diagnostics"][0]["code"], "name_directory_mismatch")

    def test_unreadable_encoding_and_oversized_manifest(self):
        path = self.skill("skills/binary-tool")
        path.write_bytes(b"\xff\xfe")
        path = self.skill("skills/large-tool")
        path.write_bytes(b"x" * (SCAN.MAX_MANIFEST_BYTES + 1))
        report = self.scan()
        self.assertEqual({d["code"] for d in report["diagnostics"]}, {"manifest_unreadable", "manifest_too_large"})

    def test_cli_missing_root_is_json_failure(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root / "missing")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["scan_complete"])
        self.assertEqual(report["diagnostics"][0]["code"], "root_unreadable")

    def test_cli_from_different_cwd(self):
        self.skill("packages/archive/skills/archive-tool")
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root)], cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["skills"]), 1)

    def test_skill_named_like_build_output_is_not_lost(self):
        self.skill("skills/build")
        report = self.scan()
        self.assertTrue(report["scan_complete"])
        self.assertEqual([s["name"] for s in report["skills"]], ["build"])

    def test_linked_config_without_skills_is_not_an_error(self):
        target = self.root / "shared-config"
        target.mkdir()
        self.link(".claude", target)
        self.assertTrue(self.scan()["scan_complete"])

    def test_missing_yaml_dependency_is_explicit(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["scan_complete"])
        self.assertIn("PyYAML", json.loads(result.stdout)["error"])

    def test_empty_and_whitespace_only_bodies_are_rejected(self):
        for index, body in enumerate(("", "\n", " \t\n\r\n")):
            with self.subTest(body=repr(body)):
                name = f"empty-{index}"
                path = self.skill("skills/" + name)
                path.write_text(f"---\nname: {name}\ndescription: Library capability.\n---\n{body}", encoding="utf-8")
        report = self.scan()
        self.assertFalse(report["scan_complete"])
        self.assertEqual(report["skills"], [])
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["body_empty"] * 3)

    def test_body_may_immediately_follow_closing_frontmatter(self):
        path = self.skill("skills/body-tool")
        path.write_text("---\nname: body-tool\ndescription: Use an existing library.\n---\nRead the linked API documentation before calling the library.\n", encoding="utf-8")
        self.assertTrue(self.scan()["scan_complete"])
        self.assertEqual(len(self.scan()["skills"]), 1)


if __name__ == "__main__":
    unittest.main()
