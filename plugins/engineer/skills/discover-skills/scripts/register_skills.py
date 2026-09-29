#!/usr/bin/env python3
"""Scan a project and create missing relative skill links for selected agents.

The default cleans invalid discovery symlinks and registers missing entries.
Valid links and ordinary files/directories are never replaced. Requires
Python 3.9+ and PyYAML. Use --dry-run for a read-only preview.
"""

import argparse
import errno
import json
import os
from pathlib import Path
import stat
import sys

from scan_skills import Scanner, yaml


TARGETS = {"codex": (".agents", "skills"), "claude": (".claude", "skills")}


def contained(path, root):
    """Check containment using canonical paths, without string prefix tricks."""
    return path == root or root in path.parents


def destination_parent(project, agent, dry_run):
    """Resolve/create the selected project directory without escaping it."""
    current = project
    for part in TARGETS[agent]:
        candidate = current / part
        if not os.path.lexists(candidate) and not dry_run:
            try:
                candidate.mkdir()
            except FileExistsError:
                # Another registration may have created the same directory.
                pass
        if os.path.lexists(candidate):
            real = candidate.resolve(strict=True)
            if not real.is_dir():
                raise NotADirectoryError(str(candidate))
            if not contained(real, project):
                raise ValueError("Discovery directory resolves outside the project: " + str(candidate))
            current = real
        else:
            current = candidate
    return current


def existing_status(destination, source):
    """Return unchanged for the same source, or a non-destructive conflict."""
    if not os.path.lexists(destination):
        return None
    try:
        if destination.resolve(strict=True) == source:
            return "unchanged", "Entry already resolves to this source"
    except (OSError, RuntimeError):
        return "conflict", "Existing entry is broken or cyclic; it was not replaced"
    return "conflict", "Existing file, directory or link belongs to a different source"


def invalid_link_reason(link):
    """Identify stale skill links; access errors are not proof of invalidity."""
    try:
        target = link.resolve(strict=True)
        if not target.is_dir():
            return "Target is not a skill directory"
        manifests = [p for p in target.iterdir() if p.name.lower() == "skill.md"]
        if not manifests:
            return "Target directory has no SKILL.md"
        if len(manifests) == 1:
            manifest = manifests[0].resolve(strict=True)
            if not stat.S_ISREG(manifest.stat().st_mode):
                return "Target SKILL.md is not a regular file"
    except (FileNotFoundError, NotADirectoryError):
        return "Target or SKILL.md no longer exists"
    except RuntimeError:
        return "Symlink loop"
    except OSError as error:
        if error.errno == errno.ELOOP:
            return "Symlink loop"
        raise
    return None


def cleanup_links(project, agents, dry_run=False):
    """Unlink only invalid direct symlink entries in selected project roots."""
    actions, blocked, planned = [], set(), set()
    seen = set()
    for agent in agents:
        logical = project.joinpath(*TARGETS[agent])
        try:
            parent = destination_parent(project, agent, dry_run=True)
            if not parent.exists() or parent in seen:
                continue
            seen.add(parent)
            entries = sorted(parent.iterdir())
        except (OSError, RuntimeError, ValueError) as error:
            actions.append({"agent": agent, "entry": str(logical), "status": "error", "reason": str(error)})
            blocked.add(agent)
            continue
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                before = entry.lstat()
                if not stat.S_ISLNK(before.st_mode):
                    continue
                target = os.readlink(entry)
                reason = invalid_link_reason(entry)
                if not reason:
                    continue
                action = {"name": entry.name, "agent": agent, "entry": str(logical / entry.name),
                          "old_target": target, "reason": reason}
                if dry_run:
                    planned.add(str(entry))
                    action["status"] = "would_remove"
                else:
                    # Recheck identity and validity immediately before unlink.
                    now = entry.lstat()
                    if (not stat.S_ISLNK(now.st_mode) or
                            (now.st_dev, now.st_ino) != (before.st_dev, before.st_ino) or
                            os.readlink(entry) != target or not invalid_link_reason(entry)):
                        action.update(status="skipped", reason="Entry changed during cleanup; left untouched")
                    else:
                        entry.unlink()
                        action["status"] = "removed"
                actions.append(action)
            except FileNotFoundError:
                # A concurrently removed entry needs no cleanup from us.
                continue
            except (OSError, RuntimeError, ValueError) as error:
                actions.append({"name": entry.name, "agent": agent, "entry": str(logical / entry.name),
                                "status": "error", "reason": str(error)})
    return actions, blocked, planned


def register(report, project_root, agents, dry_run=False, planned_removals=()):
    """Register valid unique sources; preserve conflicts and unrelated entries."""
    actions = []
    result = {"dry_run": dry_run, "agents": list(agents), "actions": actions}
    try:
        project = Path(project_root).resolve(strict=True)
        if not project.is_dir():
            raise NotADirectoryError(str(project))
        if project == Path(project.anchor) or project == Path.home().resolve():
            raise ValueError("Choose a project directory, not the filesystem root or home directory")
    except (OSError, RuntimeError, ValueError) as error:
        result.update(ok=False, error=str(error), counts={})
        return result

    roots = [Path(root) for root in report["scanned_roots"]]
    groups = {}
    for skill in report["skills"]:
        groups.setdefault(skill["name"], []).append(skill)

    projected_entries = {}
    for name, skills in sorted(groups.items()):
        for agent in agents:
            entry = project.joinpath(*TARGETS[agent], name)
            action = {"name": name, "agent": agent, "entry": str(entry)}
            actions.append(action)
            if agent == "claude" and name in {"synced", "anthropic-skills"}:
                action.update(status="conflict", reason="Name is reserved by Claude Code")
                continue
            try:
                # Existing entries are authoritative selections, even when
                # sources share a name or live outside the new-link scope.
                parent = destination_parent(project, agent, dry_run=True)
                destination = parent / name
                projected = dry_run and destination in projected_entries
                existing = projected_entries.get(destination) if projected else None
                if not projected and not (dry_run and str(destination) in planned_removals):
                    if os.path.lexists(destination):
                        existing = destination.resolve(strict=True)
                if existing is not None:
                    matching = next((s for s in skills if Path(s["skill_dir"]) == existing), None)
                    if matching and Path(matching["skill_path"]).is_file():
                        action.update(status="unchanged", source=str(existing),
                                      reason="Entry already resolves to this source" if not projected
                                      else "An earlier preview action provides this entry")
                        if projected:
                            action["projected"] = True
                    else:
                        action.update(status="conflict", reason="Existing entry belongs to a different source")
                    continue
                if len(skills) != 1:
                    action.update(status="conflict", reason="Multiple source skills share this name",
                                  sources=[s["skill_path"] for s in skills])
                    continue
                skill = skills[0]
                source = Path(skill["skill_dir"])
                action["source"] = str(source)
                if not any(contained(source, root) for root in roots):
                    action.update(status="skipped", reason="New registration requires the source in explicit scan roots; use --library-root")
                    continue
                # Verify the source still exists before creating any target.
                if not Path(skill["skill_path"]).is_file() or source.resolve(strict=True) != source:
                    raise ValueError("Source changed or disappeared after scanning")
                relative = os.path.relpath(source, parent)
                action["relative_target"] = relative
                if dry_run:
                    action["status"] = "would_create"
                    projected_entries[destination] = source
                    continue
                parent = destination_parent(project, agent, dry_run=False)
                destination = parent / name
                relative = os.path.relpath(source, parent)
                action["relative_target"] = relative
                try:
                    destination.symlink_to(relative, target_is_directory=True)
                except FileExistsError:
                    present = existing_status(destination, source)
                    if present:
                        action.update(status=present[0], reason=present[1])
                        continue
                    raise
                if destination.resolve(strict=True) != source:
                    raise ValueError("Created link did not resolve to the selected source")
                action["status"] = "created"
            except (OSError, RuntimeError, ValueError) as error:
                action.update(status="error", reason=str(error))

    counts = {}
    for action in actions:
        counts[action["status"]] = counts.get(action["status"], 0) + 1
    result.update(counts=counts, ok=report["scan_complete"] and not any(
        a["status"] in {"conflict", "error", "skipped"} for a in actions))
    return result


def synchronize(project_root, agents, library_roots=(), excludes=(), dry_run=False):
    """Clean first, then scan so removed links do not leave stale diagnostics."""
    try:
        project = Path(project_root).resolve(strict=True)
        if not project.is_dir():
            raise NotADirectoryError(str(project))
        if project in {Path(project.anchor), Path.home().resolve()}:
            raise ValueError("Choose a project directory, not the filesystem root or home directory")
    except (OSError, RuntimeError, ValueError) as error:
        return {"ok": False, "error": str(error)}
    cleanup, blocked, planned = cleanup_links(project, agents, dry_run)
    scanner = Scanner(excludes)
    for root in [project] + list(library_roots):
        scanner.scan_root(root)
    report = scanner.result()
    registration = register(report, project, [a for a in agents if a not in blocked], dry_run, planned)
    registration["agents"] = list(agents)
    registration["actions"] = cleanup + registration["actions"]
    counts = {}
    for action in registration["actions"]:
        counts[action["status"]] = counts.get(action["status"], 0) + 1
    registration["counts"] = counts
    registration["ok"] = report["scan_complete"] and not any(
        a["status"] in {"conflict", "error", "skipped"} for a in registration["actions"])
    report.update(registration=registration, ok=registration["ok"])
    return report


def main(argv=None):
    """Emit scan and registration results as a single machine-readable report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--agent", required=True, choices=("codex", "claude", "both"))
    parser.add_argument("--library-root", action="append", default=[], type=Path)
    parser.add_argument("--exclude-dir", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating or deleting directories or links")
    args = parser.parse_args(argv)
    if yaml is None:
        print(json.dumps({"ok": False, "error": "PyYAML is required; see scripts/requirements.txt"}))
        return 2
    agents = ["codex", "claude"] if args.agent == "both" else [args.agent]
    report = synchronize(args.project_root, agents, args.library_root, args.exclude_dir, args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
