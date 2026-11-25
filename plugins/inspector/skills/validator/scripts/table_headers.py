#!/usr/bin/env python3
"""Check rendered Markdown tables against the assets shipped with this plugin."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
from read_section import sections


HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*$")


def visible_lines(text):
    """Preserve line numbers, dropping code fences and HTML comments."""
    fence = None
    comment = False
    for number, line in enumerate(text.splitlines(), 1):
        mark = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if mark and mark[1].startswith(fence) and not mark[2].strip():
                fence = None
            continue
        if mark and not comment:
            fence = mark[1]
            continue
        if comment:
            _, end, line = line.partition("-->")
            comment = not bool(end)
        while "<!--" in line:
            prefix, _, rest = line.partition("<!--")
            _, end, tail = rest.partition("-->")
            line = prefix + tail
            comment = not bool(end)
        yield number, line


def cells(line):
    value = line.strip().removeprefix("|")
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]
    return [x.strip().replace(r"\|", "|") for x in re.split(r"(?<!\\)\|", value)]


def scan(text):
    headings, tables, stack = [], [], []
    table = None
    previous = None
    for n, line in visible_lines(text):
        h = HEADING.match(line)
        if h:
            level = len(h[1])
            stack = [parent for parent in stack if parent["level"] < level]
            heading = dict(line=n, level=level, title=h[2])
            stack.append(heading)
            headings.append(heading)
        if "|" not in line:
            table = previous = None
            continue
        row = cells(line)
        if previous and previous[0] == n - 1 and all(re.fullmatch(r":?-{2,}:?", x) for x in row):
            table = dict(line=n-1, section=[h["title"] for h in stack],
                         fields=previous[1], separator_width=len(row), rows=[])
            tables.append(table)
        elif table:
            table["rows"].append((n, row))
        previous = n, row
    return headings, tables


# Headers are read from the templates. An absent optional heading does not
# require a table. Applicability of those headings is checked against the project.
SECTIONS = {
    "design-index": {"2.3": False, "3.3": False, "6.1": True},
    "design-module": {"1.1": False, "1.2": False, "1.3": False, "8.2": True, "8.3": True, "10": True},
    "api-service": {"API 模块索引": True},
    "test-report": {"E": True, "F": True},
    "unit-test-report": {"A.2": True},
    "integration-test-report": {"B.2": True},
}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
LINK = re.compile(r"\[((?:`[^`\n]*`|\\.|[^\[\]\\`\n])+)\]\(([^()\s]+)\)")


def heading_key(title):
    matched = re.match(r"^([A-Z]|\d+)(?:\.(\d+))?\.?\s+", title)
    if matched:
        return ".".join(x for x in matched.groups() if x)
    return title.split("（")[0].strip()


def rules_for(kind):
    kinds = ["test-report", "unit-test-report", "integration-test-report"] if kind == "report" else [kind]
    rules = {}
    for part in kinds:
        _, models = scan((ASSETS / (part + ".md")).read_text(encoding="utf-8"))
        for table in models:
            key = heading_key(table["section"][-1])
            if key in SECTIONS[part]:
                rules[key] = (table["fields"], SECTIONS[part][key])
    return rules


def link_problem(cell, file, anchor_cache, *, definition):
    found = LINK.findall(cell)
    if not found:
        return "名称须链接到对应文档、设计定义或证据"
    for label, href in found:
        if not label.strip():
            return "缺少链接名称"
        url = urlsplit(href)
        if url.scheme or url.netloc:
            continue
        target = (file.parent / unquote(url.path)).resolve() if url.path else file
        if not target.is_file():
            return "目标文件不存在: " + href
        fragment = unquote(url.fragment)
        if fragment and re.fullmatch(r"L[1-9]\d*(?:-L?[1-9]\d*)?", fragment):
            if definition:
                return "定义链接须指向设计章节: " + href
            numbers = [int(n) for n in re.findall(r"\d+", fragment)]
            if max(numbers) > len(target.read_bytes().splitlines()) or numbers[0] > numbers[-1]:
                return "行号超出范围: " + href
        elif definition and not fragment:
            return "名称须定位到具体定义: " + href
        elif fragment and target.suffix.lower() == ".md":
            if target not in anchor_cache:
                try:
                    heads = sections(target.read_text(encoding="utf-8").splitlines(keepends=True))
                    anchor_cache[target] = {a for h in heads for a in [h["anchor"], *h["aliases"]]}
                except ValueError:
                    return "需用项目 Markdown 解析器核对锚点: " + href
            if fragment not in anchor_cache[target]:
                return "目标锚点不存在: " + href
    return None


def check(path, kind):
    heads, tables = scan(path.read_text(encoding="utf-8"))
    rules = rules_for(kind)
    present = {heading_key(h["title"]) for h in heads}
    if kind == "report" and "B" not in present and not any(k.startswith("B.") for k in present):
        rules.pop("B.2")
    groups = {k: [] for k in rules}
    for table in tables:
        for parent in reversed(table["section"]):
            key = heading_key(parent)
            if key in groups:
                groups[key].append(table)
                break
    issues, checked = [], []
    anchor_cache = {}
    for section, (expected, required) in rules.items():
        if not groups[section] and (required or section in present):
            issues.append(dict(section=section, problem="缺少模板表格", expected=expected))
        for table in groups[section]:
            checked.append(section)
            if table["fields"] != expected:
                issues.append(dict(section=section, line=table["line"], problem="表头不符", expected=expected, actual=table["fields"]))
                continue
            if table["separator_width"] != len(expected) or not table["rows"]:
                issues.append(dict(section=section, line=table["line"], problem="分隔行列数错误或表格无数据行"))
            for n, cells_in_row in table["rows"]:
                if len(cells_in_row) != len(expected):
                    issues.append(dict(section=section, line=n, problem="数据行列数不符"))
                    continue
                fields = dict(zip(expected, cells_in_row))
                for field, value in fields.items():
                    if not value:
                        issues.append(dict(section=section, line=n, column=field, problem="字段为空"))
                for field in ["共享能力", "依赖模块", "关联接口或类型", "调用接口", "验收条件", "模块", "问题", "验收项"]:
                    if field not in fields:
                        continue
                    value = fields[field]
                    if field == "问题" and value.strip("` ") in {"无", "无发现"}:
                        continue
                    if field == "验收项" and fields.get("结果", "").strip("` ") in {"FAIL", "INCOMPLETE"} and any(note in value for note in ("无设计依据", "设计依据缺失", "缺少设计依据")):
                        continue
                    definition = field in {"共享能力", "关联接口或类型", "调用接口", "验收条件", "验收项"}
                    problem = link_problem(value, path, anchor_cache, definition=definition)
                    if problem:
                        issues.append(dict(section=section, line=n, column=field, problem=problem))
                if "责任归属" in fields and fields["结果"].strip("` ") in {"FAIL", "INCOMPLETE"}:
                    for field in ("未满足项", "责任归属"):
                        if fields[field].strip("` ") in {"", "无", "—", "-"}:
                            issues.append(dict(section=section, line=n, column=field, problem="未通过项须说明缺口和归属"))
    return dict(file=str(path), checked=checked, issues=issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = ["report"] if (ASSETS / "test-report.md").is_file() else ["design-index", "design-module", "api-service"]
    parser.add_argument("--kind", choices=options, required=True)
    parser.add_argument("document", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.document.resolve(), args.kind)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False))
    return bool(result["issues"])


if __name__ == "__main__":
    raise SystemExit(main())
