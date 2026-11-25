#!/usr/bin/env python3
"""Prepare and reconcile an independent semantic review from a design inventory.

The worklist is a set of leads, not verdicts. Only the reviewer can establish
whether the target, reachable implementation branches and test assertions agree.
Input and output are local JSON; the script writes only to stdout.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from binding_review import binding_items


# Restrictive language makes it valuable to check both directions of a condition.
RESTRICTION = re.compile(r"只有|仅当|当且仅当|仅在|只在|才允许|仅允许|\bonly\b|\bif and only if\b", re.I)
TRANSITION = re.compile(r"重试|回退|回滚|降级|恢复|补偿|回写|切换|重连|\b(?:retry|rollback|fallback|recover)\b", re.I)


def row_signals(row, repeated):
    flags = []
    if row["line"] in repeated:
        flags.append("多个功能共用入口")
    # Contract rows retain their exact text and destinations. The reviewer
    # checks identity at the call site, including entries written in prose.
    if any(term in row["section"] for term in ("依赖", "调用方", "契约归属")):
        flags.append("核对使用方式与目标契约")
    return flags


def snapshot_contents(docroot, inventory):
    docs = inventory["documents"]
    snapshot = inventory.get("snapshot")
    if not snapshot or snapshot.get("scope") not in ("all", "files"):
        raise ValueError("unversioned or invalid inventory; regenerate with audit_design.py --view inventory")
    hashes = snapshot["sha256"]
    if not docs or not set(docs).issubset(hashes):
        raise ValueError("inventory lacks document fingerprints; regenerate it")
    if snapshot["scope"] == "all":
        current = {str(f.relative_to(docroot)) for f in docroot.rglob("*.md")}
        if current != set(docs):
            raise ValueError("design document set changed; regenerate the inventory")

    contents = {}
    for name, expected in hashes.items():
        file = (docroot / name).resolve()
        if not file.is_relative_to(docroot):
            raise ValueError("inventory path outside design directory: " + name)
        data = file.read_bytes() if file.is_file() else None
        actual = hashlib.sha256(data).hexdigest() if data is not None else None
        if actual != expected or (name in docs and data is None):
            raise ValueError("document changed: " + name + "; regenerate the inventory")
        if name in docs:
            contents[name] = data.decode("utf-8")
    return contents


def worklist(docs, contents):
    result = []
    for filename, doc in docs.items():
        lines = contents[filename].splitlines()
        issues = doc["format"]
        result.append(dict(file=filename, line=1, kind="文件", template=doc["template"],
                           format=issues, cues=["核对文档结构与模板适用项"] if any(issues.values()) else []))
        for finding in doc["object_findings"]:
            result.append(dict(file=filename, line=finding["line"], kind="格式·" + finding["rule"],
                               text=finding["detail"], cues=["逐项核实成稿格式"]))
        for case in doc.get("case_rows", []):
            result.append(dict(file=filename, kind="用例归属", cues=[], **case))
        heads = doc["headings"]
        repeated = {n for rows in doc["shared_entries"].values() for n, _ in rows}
        # One row can carry several targets: retain all cells and destinations.
        for row in doc["contracts"]:
            result.append(dict(file=filename, line=row["line"], kind="契约行",
                               section=row["section"], cues=row_signals(row, repeated),
                               text=" | ".join(row["fields"]), links=row["links"]))
        # Every concrete section has a review unit, even with no extracted rows or trigger words.
        for h in heads:
            if h["level"] >= 2:
                result.append(dict(file=filename, line=h["line"], kind="章节", section=h["title"], cues=[]))
        positions = [h["line"] for h in heads]
        for n, original in enumerate(lines, 1):
            line = doc["prose_overrides"].get(str(n), original)
            if not RESTRICTION.search(line):
                continue
            i = bisect_right(positions, n) - 1
            cues = ["核实限定条件是否与实际分支双向对应"]
            if TRANSITION.search(line):
                cues.append("追溯状态转换的触发来源及全部分类")
            result.append(dict(file=filename, line=n, kind="条件", section=heads[i]["title"] if i >= 0 else "",
                               cues=cues, text=line.strip()))
    # Group same-line findings under one decision, retaining every affected literal.
    grouped = {}
    for item in result:
        k = key(item)
        if k in grouped and item["kind"].startswith("格式·"):
            grouped[k]["text"] += "、" + item["text"]
        else:
            grouped[k] = item
    return list(grouped.values())


def key(entry):
    return f"{entry['file']}:{entry['line']}:{entry['kind']}"


def reconcile(items, decisions):
    """A group of units can share evidence only when all refer to the same assertion."""
    if not isinstance(decisions, list):
        raise ValueError("decisions must be an array")
    known = {key(item) for item in items}
    covered = set()
    totals = Counter()
    for record in decisions:
        status = record["status"]
        if status not in ("符合", "偏差", "未核实", "不适用"):
            raise ValueError("unknown status: " + status)
        if not record.get("basis", "").strip():
            raise ValueError("missing basis for review decision")
        if status in ("符合", "偏差") and not record.get("evidence"):
            raise ValueError("verified decisions require evidence locations")
        for k in record["items"]:
            if k not in known or k in covered:
                raise ValueError("unknown or repeated review item: " + k)
            covered.add(k)
            totals[status] += 1
    return dict(total=len(known), reviewed=dict(totals), unaccounted=sorted(known - covered))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path, help="design directory used for the inventory")
    ap.add_argument("--inventory", required=True, type=Path, help="audit_design.py --view inventory JSON")
    ap.add_argument("--view", choices=("all", "priority", "summary", "bindings", "cases"), default="all")
    ap.add_argument("--consumer", action="append", default=[], metavar="MODULE=PATH",
                    help="limit binding source lookup to this consumer’s actual production path; repeatable")
    ap.add_argument("--decisions", type=Path, help="reconcile JSON containing inventory_sha256 and decisions")
    args = ap.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        docs = inventory["documents"]
        contents = snapshot_contents(args.root.resolve(), inventory)
        # Bind decisions to the exact document set, template rules and extracted items.
        canonical = json.dumps(inventory, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        items = worklist(docs, contents)
        if args.consumer and args.view != "bindings":
            raise ValueError("--consumer applies to --view bindings")
        if args.view == "bindings":
            bindings = list(binding_items(docs, args.root.resolve().parent, args.consumer))
            if not args.decisions:
                for binding in bindings:
                    print(json.dumps(binding, ensure_ascii=False))
                return 0
        if args.view == "cases":
            if any(doc["template"] == "design-module.md" and "case_rows" not in doc for doc in docs.values()):
                raise ValueError("inventory lacks scenario rows; regenerate it with the current architect")
            if any(doc["template"] == "design-module.md" and not doc.get("rendering", {}).get("parser") for doc in docs.values()):
                raise ValueError("scenario links were not rendered; use an available renderer before reconciliation")
            case_items = [item for item in items if item["kind"] == "用例归属"]
            if not args.decisions:
                for item in case_items:
                    print(json.dumps(dict(id=key(item), **item), ensure_ascii=False))
                return 0
        if args.decisions:
            record = json.loads(args.decisions.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or record.get("inventory_sha256") != digest:
                raise ValueError("decisions do not match this inventory; review the current snapshot")
            if args.view in ("bindings", "cases"):
                required = ({b["id"] for b in bindings} if args.view == "bindings"
                            else {key(item) for item in case_items})
                decisions = []
                for decision in record["decisions"]:
                    relevant = [i for i in decision["items"] if i in required]
                    if relevant:
                        decisions.append(dict(decision, items=relevant))
                items = [i for i in items if key(i) in required]
                report = reconcile(items, decisions)
            else:
                report = reconcile(items, record["decisions"])
            print(json.dumps(dict(inventory_sha256=digest, **report), ensure_ascii=False))
            return int(bool(report["unaccounted"]))
        if args.view == "summary":
            report = dict(inventory_sha256=digest, documents=len(docs), items=dict(Counter(i["kind"] for i in items)),
                          priority=dict(Counter(cue for i in items for cue in i["cues"])))
            print(json.dumps(report, ensure_ascii=False))
        else:
            for item in items:
                if args.view == "all" or item["cues"]:
                    print(json.dumps(dict(id=key(item), **item), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
