#!/usr/bin/env python3
"""Read-only inventory of repository and explicitly selected library skills.

Requires Python 3.9+ and PyYAML. Never executes discovered skills or changes
discovery entries. JSON goes to stdout; incomplete scans return exit status 1.
"""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

try:
    import yaml
except ImportError:
    yaml = None


EXCLUDED_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
    ".next", ".nuxt", ".dart_tool", ".gradle", "build", "dist", "target",
    "coverage", ".tox", ".pnpm-store",
})
HOST_DIRS = {".agents": "codex", ".claude": "claude-code", ".codex": "legacy-codex"}
MAX_MANIFEST_BYTES = 256 * 1024


def host_for(path):
    """Return the candidate host only for a direct standard discovery entry."""
    if path.parent.parent.name == "skills":
        return HOST_DIRS.get(path.parent.parent.parent.name)
    return None


class Scanner:
    """Collect a deterministic inventory, deduplicating by real manifest path."""

    def __init__(self, extra_excludes=()):
        self.excludes = EXCLUDED_DIRS | frozenset(extra_excludes)
        self.skills = {}
        self.visited = set()
        self.roots = []
        self.diagnostics = []
        self.skipped_links = set()

    def problem(self, code, path, message):
        """Record a failure without silently treating it as an empty result."""
        item = {"code": code, "path": str(path), "message": message}
        if item not in self.diagnostics:
            self.diagnostics.append(item)

    def manifest(self, path):
        """Read metadata only; unknown host extension fields are accepted."""
        try:
            real = path.resolve(strict=True)
            if real in self.skills:
                self.add_entry(self.skills[real], path)
                return
            if not stat.S_ISREG(real.stat().st_mode):
                self.problem("not_regular_file", path, "SKILL.md must be a regular file")
                return
            with real.open("rb") as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                self.problem("manifest_too_large", path, "Manifest exceeds the 256 KiB scan limit")
                return
            text = raw.decode("utf-8-sig")
        except (OSError, RuntimeError, UnicodeError) as error:
            self.problem("manifest_unreadable", path, str(error))
            return

        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
        if not match:
            self.problem("frontmatter_missing", path, "Expected a closed YAML frontmatter block")
            return
        try:
            meta = yaml.safe_load(match.group(1))
        except yaml.YAMLError as error:
            # Do not echo arbitrary YAML values (which can contain credentials).
            mark = getattr(error, "problem_mark", None)
            suffix = " at frontmatter line " + str(mark.line + 1) if mark else ""
            self.problem("frontmatter_invalid", path, "Cannot parse YAML" + suffix)
            return
        if not isinstance(meta, dict):
            self.problem("frontmatter_invalid", path, "YAML frontmatter must be a mapping")
            return
        name, description = meta.get("name"), meta.get("description")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            self.problem("name_invalid", path, "Expected a 1-64 character skill name")
            return
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            self.problem("description_invalid", path, "Expected a nonempty description of at most 1024 characters")
            return
        if name != real.parent.name:
            self.problem("name_directory_mismatch", path, "Skill name differs from its source directory name")
            return
        if not text[match.end():].strip():
            self.problem("body_empty", path, "SKILL.md must include a nonempty Markdown body after frontmatter")
            return
        when = meta.get("when_to_use")
        record = {
            "name": name,
            "description": description.strip(),
            "when_to_use": when.strip() if isinstance(when, str) else None,
            "skill_path": str(real),
            "skill_dir": str(real.parent),
            "paths": [],
            "discovery_entries": [],
        }
        self.skills[real] = record
        self.add_entry(record, path)

    @staticmethod
    def add_entry(record, path):
        """Preserve aliases while keeping only one record for a source file."""
        spelling = str(path)
        if spelling not in record["paths"]:
            record["paths"].append(spelling)
        host = host_for(path)
        if host:
            entry = {"host": host, "path": str(path.parent)}
            if entry not in record["discovery_entries"]:
                record["discovery_entries"].append(entry)

    def skill_entry(self, directory):
        """Inspect a skill-folder entry without recursively following links."""
        try:
            target = directory.resolve(strict=True)
            if not target.is_dir():
                self.problem("entry_not_directory", directory, "Discovery entry is not a directory")
                return
            manifests = sorted(p for p in target.iterdir() if p.name.lower() == "skill.md")
        except (OSError, RuntimeError) as error:
            self.problem("entry_unreadable", directory, str(error))
            return
        if len(manifests) != 1:
            self.problem("entry_manifest_count", directory, "Expected exactly one SKILL.md in the entry directory")
            return
        self.manifest(directory / manifests[0].name)

    def discovery_root(self, directory):
        """Inspect direct entries of a host skills directory, including links."""
        try:
            for entry in sorted(directory.iterdir()):
                if not entry.name.startswith(".") and (entry.is_dir() or entry.is_symlink()):
                    self.skill_entry(entry)
        except (OSError, RuntimeError) as error:
            self.problem("discovery_root_unreadable", directory, str(error))

    def scan_root(self, requested):
        """Walk files in an explicit root, pruning caches and arbitrary links."""
        spelling = Path(os.path.abspath(os.path.expanduser(str(requested))))
        try:
            root = spelling.resolve(strict=True)
            if not root.is_dir():
                raise NotADirectoryError(str(root))
        except (OSError, RuntimeError) as error:
            self.problem("root_unreadable", spelling, str(error))
            return
        if str(root) not in self.roots:
            self.roots.append(str(root))

        def walk_error(error):
            self.problem("directory_unreadable", error.filename, str(error))

        for current, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            current = Path(current)
            if current in self.visited:
                dirs[:] = []
                continue
            self.visited.add(current)
            # A host's config/cache directory is not a library inventory root.
            if current.name in HOST_DIRS:
                dirs[:] = [name for name in dirs if name == "skills"]
            if current.name == "skills" and current.parent.name in HOST_DIRS:
                self.discovery_root(current)

            manifests = sorted(name for name in files if name.lower() == "skill.md")
            if len(manifests) > 1:
                self.problem("multiple_manifests", current, "Multiple case variants of SKILL.md")
            elif manifests:
                self.manifest(current / manifests[0])

            keep = []
            for name in sorted(dirs):
                child = current / name
                if name in self.excludes:
                    # A skill can itself be named "build" or "coverage".
                    # Still inventory its direct manifest without descending
                    # into an otherwise excluded directory's resources.
                    if current.name == "skills":
                        try:
                            if any(p.name.lower() == "skill.md" for p in child.iterdir()):
                                self.skill_entry(child)
                        except OSError as error:
                            self.problem("directory_unreadable", child, str(error))
                    continue
                if child.is_symlink():
                    if current.name == "skills":
                        self.skill_entry(child)
                    elif name == "skills" and current.name in HOST_DIRS:
                        self.discovery_root(child)
                    elif name in HOST_DIRS:
                        candidate = child / "skills"
                        if candidate.exists() or candidate.is_symlink():
                            self.discovery_root(candidate)
                    else:
                        self.skipped_links.add(str(child))
                    continue
                keep.append(name)
            dirs[:] = keep
            # os.walk puts broken directory links in files, not dirs.
            if current.name == "skills":
                for name in sorted(files):
                    child = current / name
                    if child.is_symlink() and name.lower() != "skill.md":
                        self.skill_entry(child)

    def result(self):
        """Report completeness within the declared roots and exclusions."""
        records = sorted(self.skills.values(), key=lambda x: (x["name"], x["skill_path"]))
        names = {}
        for item in records:
            item["paths"].sort()
            item["discovery_entries"].sort(key=lambda x: (x["host"], x["path"]))
            names.setdefault(item["name"], []).append(item["skill_path"])
        return {
            "schema_version": 1,
            "scan_complete": not self.diagnostics,
            "scanned_roots": sorted(self.roots),
            "excluded_dir_names": sorted(self.excludes),
            "skipped_symlink_directories": sorted(self.skipped_links),
            "skills": records,
            "same_name_skills": [{"name": n, "skill_paths": paths} for n, paths in sorted(names.items()) if len(paths) > 1],
            "diagnostics": sorted(self.diagnostics, key=lambda x: (x["path"], x["code"])),
        }


def main(argv=None):
    """Parse explicit roots and emit JSON without changing the filesystem."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path, help="Project directory to inventory")
    parser.add_argument("--library-root", action="append", default=[], type=Path,
                        help="Also scan this library (repeatable, including selected dependencies)")
    parser.add_argument("--exclude-dir", action="append", default=[],
                        help="Additional directory basename to prune (repeatable)")
    args = parser.parse_args(argv)
    if yaml is None:
        print(json.dumps({"scan_complete": False, "error": "PyYAML is required; see scripts/requirements.txt"}))
        return 2
    scanner = Scanner(args.exclude_dir)
    for root in [args.project_root] + args.library_root:
        scanner.scan_root(root)
    report = scanner.result()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["scan_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
