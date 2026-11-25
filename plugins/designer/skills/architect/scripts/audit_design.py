#!/usr/bin/env python3
"""Inventory template sections, table fields and contract locators. Output JSON to stdout.

This is a worklist, not a compliance verdict. A source/requirement/test review
is needed even when every structural check passes. Complex Markdown and custom
layouts require the caller to verify the corresponding items separately.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
from document_format import check_objects, project_file_references
from design_header import check_header, header_schema, title_of
from case_locations import check_cases, definition_role, external_case_references
from rendered_prose import collect_declarations, parse_tokens, review_rendering
from read_section import sections
from table_headers import scan, visible_lines


ASSETS = Path(__file__).resolve().parent.parent / "assets"
# Brackets in inline code are part of the label (for example, a slice type).
LINK = re.compile(r"\[((?:`[^`\n]*`|\\.|[^\[\]\\`\n])+)\]\(([^()\s]+)\)")
BARE = re.compile(r"§\s*\d+(?:\.\d+)*(?:\s*[/、,，]\s*§?\s*\d+(?:\.\d+)*)*")
def infer_template(path):
    if path == Path("index.md"):
        return "design-index.md"
    if path == Path("visual-spec.md"):
        return "visual-spec.md"
    if path.parts[0] == "external-service":
        return "api-service.md" if path.name == "index.md" else "api-module.md"
    if len(path.parts) == 2 and path.name == "index.md":
        return "design-module.md"
    return None


def section_key(title):
    num = re.match(r"^(\d+(?:\.\d+)*)(?:[.、]\s*|\s+)", title)
    return num[1] if num else title.split("（")[0].strip()


def schema(text):
    heads, tables = scan(text)
    fixed = defaultdict(list)
    heading_at = {h["line"]: h for h in heads}
    current = ""
    for n, line in visible_lines(text):
        if n in heading_at:
            current = section_key(heading_at[n]["title"])
        label = re.match(r"^(?:- )?\*\*([^*]+)\*\*\s*[:：]", line)
        if label and current in ("1", "5.3", "7", "8.1", "8.3", "8.4") and not any(
                word in line for word in ("按需", "仅有", "无则", "没有时", "可省略")):
            fixed[current].append(label[1])
    case_types = []
    for table in tables:
        if "测试场景" in table["fields"] and "类型" in table["fields"] and table["rows"]:
            case_types = table["rows"][0][1][table["fields"].index("类型")].strip("{} ").split("/")
    return dict(headings=[h["title"] for h in heads if h["level"] >= 2], fixed_labels=fixed,
                case_types=case_types, tables=[dict(section=t["section"][1:], fields=t["fields"]) for t in tables])


def audit(text, spec):
    heads, tables = scan(text)
    issues = defaultdict(list)
    contracts = []
    shared_entries = defaultdict(list)
    if spec.get("name") == "design-module.md":
        for heading in heads:
            if re.fullmatch(r"(?:[0-9.]+\s+)?实现映射(?:[（(].*[）)])?", heading["title"]):
                issues["obsolete_implementation_mapping"].append(heading["line"])
    observed = {section_key(h["title"]): h["title"] for h in heads if h["level"] == 2}
    for title in spec.get("top", []):
        if title not in observed.values():
            issues["section_missing_or_renamed"].append(dict(expected=title, actual=observed.get(section_key(title))))
    for t in tables:
        header = t["fields"]
        where = t["section"][-1] if t["section"] else ""
        key = section_key(where)
        # A numbered section may contain several alternative or conditional tables.
        # List expectations for comparison; matching the table's shape is not proof of applicability.
        candidates = [s["fields"] for s in spec.get("tables", []) if s["section"] and section_key(s["section"][-1]) == key]
        if candidates and header not in candidates:
            issues["compare_table_to_template"].append(dict(line=t["line"], section=where, actual=header, expected=candidates))
        for n, row in t["rows"]:
            if len(row) != len(header):
                issues["table_width"].append(n)
            for column, value in enumerate(row):
                if BARE.fullmatch(value.strip("*` ")):
                    issues["bare_section_reference"].append(dict(line=n, section=where, column=column+1, value=value))
            index = 'API 定义' in header and '功能' in header
            dependency = any(word in where for word in ("依赖", "调用方", "契约归属"))
            if not (dependency or index):
                continue
            if spec.get("name") == "design-module.md":
                target_cell = row[-1] if key == "1.1" and len(row) == 3 else None
                if index and len(row) > header.index("API 定义"):
                    target_cell = row[header.index("API 定义")]
                for _, href in LINK.findall(target_cell or ""):
                    url = urlsplit(href)
                    line_anchor = re.fullmatch(r"L\d+(?:[-:]L?\d+)?", url.fragment)
                    if line_anchor or (url.path and not url.fragment and not url.scheme and not url.netloc):
                        issues["verify_design_definition_target"].append(dict(line=n, href=href))
            links = [dict(label=m[1], href=m[2]) for value in row for m in LINK.finditer(value)]
            contracts.append(dict(line=n, section=where, fields=row, links=links))
            if index and len(row) > header.index("API 定义"):
                for _, href in LINK.findall(row[header.index("API 定义")]):
                    shared_entries[href].append((n,row[0]))
    # Report absent template tables as review items. Optional sections and substituted
    # project templates still require an applicability decision by the reviewer.
    present = {(section_key(t["section"][-1]) if t["section"] else "", tuple(t["fields"])) for t in tables}
    for expected in spec.get("tables", []):
        if expected["section"] and (section_key(expected["section"][-1]), tuple(expected["fields"])) not in present:
            issues["verify_missing_or_conditional_table"].append(expected)
    # Keep a sparse projection so independently installed skills scan exactly the
    # same visible prose without maintaining two Markdown parsers.
    visible = dict(visible_lines(text))
    object_findings = check_objects(text, visible, spec.get("name"), tables)
    prose_overrides = {n: visible.get(n, "") for n, line in enumerate(text.splitlines(), 1)
                       if visible.get(n, "") != line}
    locators = [dict(line=n, label=m[1], href=m[2]) for n, line in visible.items()
                for m in LINK.finditer(line) if "#" in m[2]]
    return dict(template=spec.get("name"), object_findings=object_findings, prose_overrides=prose_overrides, headings=heads,
                tables=[dict(line=t["line"], section=t["section"], fields=t["fields"],
                             rows=[n for n,_ in t["rows"]]) for t in tables],
                format=issues, contracts=contracts, locators=locators,
                shared_entries={k:v for k,v in shared_entries.items() if len(v)>1})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Project design-document directory")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--file", action="append", help="Audit a changed or impacted document relative to --root; repeat for each")
    scope.add_argument("--all", action="store_true", help="Audit the whole design-document directory")
    parser.add_argument("--view", choices=["summary","inventory","contracts","format","rendered"], default="summary")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("design-document directory does not exist")
    files = [root / name for name in args.file] if args.file else sorted(root.rglob("*.md"))
    if not files or any(not f.resolve().is_relative_to(root) or not f.is_file() for f in files):
        parser.error("expected Markdown files within the authorized design directory")
    specs = {}
    for f in ASSETS.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        spec = schema(text)
        spec["header_fields"] = header_schema(parse_tokens(text))
        heads, _ = scan(text)
        spec.update(name=f.name, top=[h["title"] for h in heads if h["level"]==2
                                     and "按需" not in h["title"] and f.name!="visual-spec.md"])
        specs[f.name] = spec
    docs = {}
    anchor_cache = {}
    contents = {}
    hashes = {}

    def read_document(path):
        # Use identical bytes for the digest, section parsing and anchor resolution.
        if path not in contents:
            if path.is_file():
                data = path.read_bytes()
                contents[path] = data.decode("utf-8")
                hashes[str(path.relative_to(root))] = hashlib.sha256(data).hexdigest()
            else:
                contents[path] = None
                hashes[str(path.relative_to(root))] = None
        return contents[path]

    # Extensionless, mixed-case project entry files also occur as plain literals in prose.
    project_names = sorted(p.name for p in root.parent.iterdir()
                           if re.fullmatch(r"[A-Z][A-Za-z0-9_-]*[a-z][A-Za-z0-9_-]*", p.name) and p.is_file())
    @lru_cache(maxsize=None)
    def link_target(source, href):
        url = urlsplit(href)
        if url.scheme or url.netloc or not url.fragment or Path(unquote(url.path)).is_absolute():
            return None, []
        target = (source.parent / unquote(url.path)).resolve() if url.path else source
        if not target.is_relative_to(root) or target.suffix != ".md" or read_document(target) is None:
            return None, []
        if target not in anchor_cache:
            try:
                anchors = defaultdict(list)
                parents = []
                for h in sections(read_document(target).splitlines(keepends=True)):
                    parents = [p for p in parents if p["level"] < h["level"]] + [h]
                    for anchor in set([h["anchor"], *h["aliases"]]):
                        anchors[anchor].append(parents)
                anchor_cache[target] = anchors
            except ValueError:
                anchor_cache[target] = None
        anchors = anchor_cache[target]
        return target, anchors.get(unquote(url.fragment), []) if anchors is not None else None

    parsed = {}
    for file in files:
        content = read_document(file)
        if content is None:
            parser.error("document disappeared during inventory: " + str(file.relative_to(root)))
        parsed[file] = parse_tokens(content)
    @lru_cache(maxsize=None)
    def parent_title(path):
        if not path.resolve().is_relative_to(root):
            return ""
        if path in parsed:
            return title_of(parsed[path])
        content = read_document(path)
        return title_of(parse_tokens(content)) if content is not None else ""

    declarations = collect_declarations(parsed.values())
    for file, tokens in parsed.items():
        name = str(file.relative_to(root))
        text = read_document(file)
        case_rows = []
        template = infer_template(Path(name))
        rendering, render_findings, blocks = review_rendering(text, include_nodes=args.view == "rendered",
                    project_names=project_names, spec=specs.get(template), tokens=tokens, declarations=declarations)
        render_findings.extend(check_header(file, root, tokens, specs.get(template), parent_title))
        if template == "design-module.md":
            @lru_cache(maxsize=None)
            def classify(href):
                target, matches = link_target(file, href)
                if not matches or len(matches) != 1:
                    return None, None
                hierarchy = matches[0]
                kind = infer_template(target.relative_to(root))
                role = definition_role(kind, hierarchy, specs.get(kind, {}).get("headings", []))
                owner = next((h["start"] for h in hierarchy if h["level"] == 3 and
                              re.match(r"^3\.\d+\s+", h["heading"])), None) if target == file else None
                return role, owner

            render_findings.extend(check_cases(tokens, classify, case_rows if args.view == "inventory" else None))

            @lru_cache(maxsize=None)
            def case_source(href):
                target, matches = link_target(file, href)
                if not matches or len(matches) != 1 or infer_template(target.relative_to(root)) != "design-module.md":
                    return None
                for heading in matches[0]:
                    category = {"8.2": "UT", "8.4": "IT"}.get(section_key(heading["heading"]))
                    if category:
                        return target.parent.name, category
                return None

            render_findings.extend(external_case_references(tokens, file.parent.name, case_source))
        if args.view == "rendered":
            docs[name] = dict(rendering=rendering, findings=render_findings, blocks=blocks)
            continue
        doc = audit(text, specs.get(infer_template(Path(name)), {}))
        doc["rendering"] = rendering
        if template == "design-module.md":
            doc["case_rows"] = case_rows
        doc["object_findings"].extend(render_findings)
        if doc["template"] in ("design-module.md", "design-index.md"):
            doc["object_findings"].extend(project_file_references(dict(visible_lines(text)), file, root, LINK))
        # Resolve each indexed contract to its actual heading for source-side review.
        for entry in doc["contracts"]:
            for link in entry["links"]:
                url = urlsplit(link["href"])
                if url.scheme or url.netloc or not url.fragment:
                    continue
                target, matches = link_target(file, link["href"])
                if target is None:
                    link["target_review"]="outside design directory or unavailable"
                    continue
                link["headings"] = [(path[-1]["start"], path[-1]["heading"]) for path in matches] if matches is not None else None
        if args.view == "format":
            if doc["object_findings"]:
                docs[name] = doc["object_findings"]
        elif args.view=="summary":
            groups=defaultdict(list)
            for item in doc["format"].get("bare_section_reference",[]):
                groups[item["section"]].append(item["line"])
            docs[name]=dict(template=doc["template"], headings=len(doc["headings"]),tables=len(doc["tables"]),
                            object_findings=len(doc["object_findings"]), format_checks={k:len(v) for k,v in doc["format"].items()},
                            bare_reference_lines=groups, contract_rows=len(doc["contracts"]), reused_index_targets=doc["shared_entries"])
        elif args.view=="contracts":
            docs[name]=doc["contracts"]
        else:
            docs[name]=doc
    if args.view == "rendered":
        print(json.dumps(docs, ensure_ascii=False))
        return int(any(not doc["rendering"]["parser"] for doc in docs.values()))
    output = dict(templates=specs if args.view == "inventory" else list(specs), documents=docs)
    if args.view == "inventory":
        output["snapshot"] = dict(scope="all" if args.all else "files", sha256=hashes)
    if args.view == "format":
        print(json.dumps(docs, ensure_ascii=False, indent=2))
        return int(bool(docs))
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__=="__main__":
    sys.exit(main())
