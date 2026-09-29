"""Registration tests using isolated projects, never the user's agent paths."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from register_skills import synchronize


class RegistrationTests(unittest.TestCase):
    """Validate immediate registration, idempotency and conflict preservation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-register-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()

    def skill(self, relative="packages/tool/skills/my-tool", name="my-tool", root=None):
        directory = (root or self.project) / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test library capability.\neffort: high\n---\n\n# Usage\n",
            encoding="utf-8")
        return directory

    def scan_and_register(self, agents=("codex", "claude"), dry_run=False, extra=()):
        return synchronize(self.project, agents, extra, dry_run=dry_run)["registration"]

    def test_creates_relative_links_for_selected_agents(self):
        source = self.skill()
        result = self.scan_and_register()
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"created": 2})
        for host in (".agents", ".claude"):
            link = self.project / host / "skills/my-tool"
            self.assertTrue(link.is_symlink())
            self.assertFalse(os.path.isabs(os.readlink(link)))
            self.assertEqual(link.resolve(), source)

    def test_second_run_does_not_recreate_correct_links(self):
        self.skill()
        self.scan_and_register()
        link = self.project / ".agents/skills/my-tool"
        before = link.lstat()
        result = self.scan_and_register()
        after = link.lstat()
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"unchanged": 2})
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_only_requested_agent_directory_is_created(self):
        self.skill()
        self.scan_and_register(("codex",))
        self.assertTrue((self.project / ".agents/skills/my-tool").is_symlink())
        self.assertFalse((self.project / ".claude").exists())

    def test_dry_run_does_not_create_directories(self):
        self.skill()
        result = self.scan_and_register(dry_run=True)
        self.assertEqual(result["counts"], {"would_create": 2})
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".claude").exists())

    def test_same_name_sources_are_not_chosen_arbitrarily(self):
        self.skill()
        self.skill("packages/other/skills/my-tool")
        result = self.scan_and_register()
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"], {"conflict": 2})
        self.assertFalse((self.project / ".agents").exists())

    def test_existing_file_is_preserved_and_broken_link_is_replaced(self):
        source = self.skill()
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.write_text("owned by user", encoding="utf-8")
        broken = self.project / ".claude/skills/my-tool"
        broken.parent.mkdir(parents=True)
        broken.symlink_to("../../missing")
        result = self.scan_and_register()
        self.assertEqual(result["counts"], {"removed": 1, "conflict": 1, "created": 1})
        self.assertEqual(entry.read_text(), "owned by user")
        self.assertEqual(broken.resolve(), source)
        self.assertEqual(result["actions"][0]["old_target"], "../../missing")

    def test_existing_directory_and_different_link_are_preserved(self):
        self.skill()
        entry = self.project / ".agents/skills/my-tool"
        entry.mkdir(parents=True)
        other = self.project / "other-data"
        other.mkdir()
        (other / "SKILL.md").write_text("---\nname: other-data\ndescription: Other library.\n---\n", encoding="utf-8")
        link = self.project / ".claude/skills/my-tool"
        link.parent.mkdir(parents=True)
        link.symlink_to(other)
        result = self.scan_and_register()
        self.assertEqual(result["counts"].get("conflict"), 2)
        self.assertFalse(entry.is_symlink())
        self.assertEqual(link.resolve(), other)

    def test_existing_standard_source_directory_is_unchanged(self):
        source = self.skill(".agents/skills/my-tool")
        result = self.scan_and_register()
        self.assertEqual(result["counts"], {"unchanged": 1, "created": 1})
        self.assertFalse(source.is_symlink())

    def test_destination_parent_outside_project_is_not_written(self):
        self.skill()
        outside = self.base / "outside"
        outside.mkdir()
        (self.project / ".agents").symlink_to(outside, target_is_directory=True)
        result = self.scan_and_register(("codex",))
        self.assertEqual(result["counts"], {"error": 1})
        self.assertEqual(list(outside.iterdir()), [])

    def test_shared_parent_inside_project_uses_real_relative_base(self):
        source = self.skill()
        shared = self.project / "shared"
        shared.mkdir()
        (self.project / ".agents").symlink_to(shared, target_is_directory=True)
        (self.project / ".claude").symlink_to(shared, target_is_directory=True)
        result = self.scan_and_register()
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"created": 1, "unchanged": 1})
        self.assertEqual((shared / "skills/my-tool").resolve(), source)

    def test_source_outside_roots_requires_explicit_library_root(self):
        outside = self.base / "library"
        source = self.skill("skills/my-tool", root=outside)
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source, target_is_directory=True)
        result = self.scan_and_register(("claude",))
        self.assertEqual(result["counts"], {"skipped": 1})
        self.assertFalse((self.project / ".claude").exists())
        result = self.scan_and_register(("claude",), extra=(outside,))
        self.assertEqual(result["counts"], {"created": 1})

    def test_existing_correct_external_entry_is_unchanged(self):
        source = self.skill("skills/my-tool", root=self.base / "external-library")
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source, target_is_directory=True)
        before = entry.lstat()
        result = self.scan_and_register(("codex",))
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"unchanged": 1})
        self.assertEqual(entry.lstat().st_ino, before.st_ino)

    def test_existing_entry_disambiguates_same_name_for_its_agent(self):
        source = self.skill()
        self.skill("packages/other/skills/my-tool")
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source, target_is_directory=True)
        result = self.scan_and_register(("codex",))
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"unchanged": 1})
        both = self.scan_and_register()
        self.assertFalse(both["ok"])
        self.assertEqual(both["counts"], {"unchanged": 1, "conflict": 1})
        self.assertFalse((self.project / ".claude").exists())

    def test_shared_directory_preview_matches_actual_action_counts(self):
        self.skill()
        shared = self.project / "shared"
        shared.mkdir()
        (self.project / ".agents").symlink_to(shared, target_is_directory=True)
        (self.project / ".claude").symlink_to(shared, target_is_directory=True)
        preview = self.scan_and_register(dry_run=True)
        self.assertTrue(preview["ok"])
        self.assertEqual(preview["counts"], {"would_create": 1, "unchanged": 1})
        self.assertTrue(preview["actions"][1]["projected"])
        self.assertFalse((shared / "skills").exists())
        actual = self.scan_and_register()
        self.assertEqual(actual["counts"], {"created": 1, "unchanged": 1})

    def test_shared_broken_entry_preview_reuses_planned_replacement(self):
        self.skill()
        shared = self.project / "shared"
        (shared / "skills").mkdir(parents=True)
        stale = shared / "skills/my-tool"
        stale.symlink_to("gone")
        (self.project / ".agents").symlink_to(shared, target_is_directory=True)
        (self.project / ".claude").symlink_to(shared, target_is_directory=True)
        preview = self.scan_and_register(dry_run=True)
        self.assertEqual(preview["counts"], {"would_remove": 1, "would_create": 1, "unchanged": 1})
        self.assertEqual(os.readlink(stale), "gone")
        actual = self.scan_and_register()
        self.assertEqual(actual["counts"], {"removed": 1, "created": 1, "unchanged": 1})

    def test_moved_project_keeps_relative_links_and_is_idempotent(self):
        self.skill()
        self.scan_and_register()
        destination = self.base / "moved-project"
        shutil.move(str(self.project), str(destination))
        self.project = destination
        result = self.scan_and_register()
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"unchanged": 2})

    def test_invalid_metadata_is_not_registered(self):
        self.skill(name="wrong-source-name")
        result = self.scan_and_register()
        self.assertFalse(result["ok"])
        self.assertEqual(result["actions"], [])
        self.assertFalse((self.project / ".agents").exists())

    def test_valid_sources_register_despite_unrelated_scan_failure(self):
        self.skill()
        invalid = self.skill("packages/bad/skills/bad-tool", name="bad-tool")
        (invalid / "SKILL.md").write_text("no frontmatter", encoding="utf-8")
        result = self.scan_and_register(("codex",))
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"], {"created": 1})

    def test_reserved_claude_name_is_not_registered(self):
        self.skill("skills/synced", name="synced")
        result = self.scan_and_register(("claude",))
        self.assertEqual(result["counts"], {"conflict": 1})

    def test_cli_immediately_registers_and_reports_json(self):
        self.skill()
        result = subprocess.run([sys.executable, str(SCRIPTS / "register_skills.py"),
                                 str(self.project), "--agent", "both"],
                                capture_output=True, text=True, cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["registration"]["counts"], {"created": 2})

    def test_cli_missing_dependency_has_no_side_effects(self):
        self.skill()
        result = subprocess.run([sys.executable, "-S", str(SCRIPTS / "register_skills.py"),
                                 str(self.project), "--agent", "codex"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("PyYAML", json.loads(result.stdout)["error"])
        self.assertFalse((self.project / ".agents").exists())

    def test_orphan_broken_link_removed_without_replacement(self):
        entry = self.project / ".agents/skills/removed-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to("../../gone")
        report = synchronize(self.project, ["codex"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["registration"]["counts"], {"removed": 1})
        self.assertFalse(os.path.lexists(entry))
        self.assertEqual(report["diagnostics"], [])
        self.assertEqual(self.scan_and_register(("codex",))["actions"], [])

    def test_cycle_link_removed(self):
        entry = self.project / ".agents/skills/loop"
        entry.parent.mkdir(parents=True)
        entry.symlink_to("loop")
        result = self.scan_and_register(("codex",))
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"], {"removed": 1})
        self.assertFalse(os.path.lexists(entry))

    def test_non_skill_target_link_removed_but_target_preserved(self):
        directory = self.project / "library-without-skill"
        directory.mkdir()
        code = directory / "code.txt"
        code.write_text("keep", encoding="utf-8")
        entry = self.project / ".agents/skills/stale"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(directory, target_is_directory=True)
        result = self.scan_and_register(("codex",))
        self.assertTrue(result["ok"])
        self.assertFalse(os.path.lexists(entry))
        self.assertEqual(code.read_text(), "keep")

    def test_link_to_file_removed_without_deleting_file(self):
        target = self.project / "ordinary.txt"
        target.write_text("keep", encoding="utf-8")
        entry = self.project / ".agents/skills/not-a-directory"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(target)
        self.scan_and_register(("codex",))
        self.assertFalse(os.path.lexists(entry))
        self.assertEqual(target.read_text(), "keep")

    def test_dry_run_previews_cleanup_and_replacement(self):
        self.skill()
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to("../../gone")
        result = self.scan_and_register(("codex",), dry_run=True)
        self.assertEqual(result["counts"], {"would_remove": 1, "would_create": 1})
        self.assertEqual(os.readlink(entry), "../../gone")

    def test_unselected_agent_and_source_links_are_not_cleaned(self):
        source = self.skill()
        inside = source / "missing-resource"
        inside.symlink_to("gone")
        other = self.project / ".claude/skills/stale"
        other.parent.mkdir(parents=True)
        other.symlink_to("../../gone")
        self.scan_and_register(("codex",))
        self.assertTrue(other.is_symlink())
        self.assertTrue(inside.is_symlink())

    def test_permission_failure_is_not_treated_as_invalid_link(self):
        source = self.skill()
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source)
        with mock.patch("register_skills.invalid_link_reason", side_effect=PermissionError("access denied")):
            result = self.scan_and_register(("codex",))
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"].get("removed", 0), 0)
        self.assertEqual(entry.resolve(), source)

    def test_invalid_yaml_link_is_reported_but_not_deleted(self):
        source = self.skill()
        (source / "SKILL.md").write_text("invalid yaml header", encoding="utf-8")
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source)
        result = self.scan_and_register(("codex",))
        self.assertFalse(result["ok"])
        self.assertEqual(entry.resolve(), source)

    def test_cleanup_shared_parent_happens_once(self):
        shared = self.project / "shared"
        (shared / "skills").mkdir(parents=True)
        (shared / "skills/stale").symlink_to("gone")
        (self.project / ".agents").symlink_to(shared, target_is_directory=True)
        (self.project / ".claude").symlink_to(shared, target_is_directory=True)
        result = self.scan_and_register()
        self.assertEqual(result["counts"], {"removed": 1})

    def test_entry_changed_to_regular_file_during_cleanup_is_preserved(self):
        entry = self.project / ".agents/skills/stale"
        entry.parent.mkdir(parents=True)
        entry.symlink_to("gone")

        def replaced_entry(path):
            path.unlink()
            path.write_text("new user file", encoding="utf-8")
            return "Target no longer exists"

        with mock.patch("register_skills.invalid_link_reason", side_effect=replaced_entry):
            result = self.scan_and_register(("codex",))
        self.assertEqual(result["counts"], {"skipped": 1})
        self.assertEqual(entry.read_text(), "new user file")

    def test_cli_cleanup_reports_success_without_stale_scan_errors(self):
        entry = self.project / ".agents/skills/stale"
        entry.parent.mkdir(parents=True)
        entry.symlink_to("gone")
        result = subprocess.run([sys.executable, str(SCRIPTS / "register_skills.py"),
                                 str(self.project), "--agent", "codex"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["registration"]["counts"], {"removed": 1})
        self.assertEqual(report["diagnostics"], [])

    def test_empty_body_is_not_registered(self):
        source = self.skill()
        (source / "SKILL.md").write_text("---\nname: my-tool\ndescription: Library capability.\n---\n", encoding="utf-8")
        report = synchronize(self.project, ["codex", "claude"])
        self.assertFalse(report["ok"])
        self.assertEqual(report["registration"]["actions"], [])
        self.assertEqual(report["diagnostics"][0]["code"], "body_empty")
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".claude").exists())

    def test_existing_link_to_empty_body_is_preserved_for_correction(self):
        source = self.skill()
        (source / "SKILL.md").write_text("---\nname: my-tool\ndescription: Library capability.\n---\n", encoding="utf-8")
        entry = self.project / ".agents/skills/my-tool"
        entry.parent.mkdir(parents=True)
        entry.symlink_to(source, target_is_directory=True)
        result = self.scan_and_register()
        self.assertFalse(result["ok"])
        self.assertEqual(entry.resolve(), source)
        self.assertFalse((self.project / ".claude").exists())

    def test_cli_reports_empty_body_and_creates_nothing(self):
        source = self.skill()
        (source / "SKILL.md").write_text("---\nname: my-tool\ndescription: Library capability.\n---\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "register_skills.py"),
                                 str(self.project), "--agent", "both"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "body_empty")
        self.assertFalse((self.project / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
