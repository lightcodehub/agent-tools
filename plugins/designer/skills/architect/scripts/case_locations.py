"""Check rendered scenario links and their group scope in module §8.2 and §8.4."""
import re
from collections import defaultdict

from rendered_literals import rendered_text
from rendered_prose import rendered_tables, table_fields


NUMBER = re.compile(r"^(\d+(?:\.\d+)*)(?:[.、]\s*|\s+)(.+)$")
GROUP_LABEL = re.compile(r"^(?:本组|(?:对应|适用|覆盖|验证|关联|所属)?(?:功能|共享规则|用例组|分组|归属))\s*[:：]")
GENERIC = {"内部设计与共享规则", "内部职责与协作", "共享规则与定义", "共享规则", "共享定义",
           "功能索引", "功能行为与接口", "函数/方法接口", "函数接口", "方法接口", "验证关联"}
CASE_SECTIONS = {"8.2": ("UT", "测试场景", "测试场景"), "8.4": ("IT", "场景与输入", "集成测试场景")}
CASE = r"([A-Za-z0-9_]+(?:[-.][A-Za-z0-9_]+)*?-(?:UT|IT)-)(\d+)"
CASE_ID = re.compile(CASE)
CASE_RANGE = re.compile(CASE + r"\s*(?:至|到|[~～–—-]|\.\.)\s*" + CASE)
INDIRECT = re.compile(r"不计入|不覆盖|未覆盖|待核实|仅(?:为|作|用于)(?:准备|前置|观察|观测)")


def reverse_cases(tokens):
    """Collect leads only from the owning feature's direct verification subsection."""
    explicit = defaultdict(dict)
    ranges = defaultdict(list)
    chapter = feature = verification = None
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            title = rendered_text(tokens[i + 1])
            number = NUMBER.match(title)
            if level <= 2:
                chapter = number[1] if level == 2 and number else None
            if level <= 3:
                feature = (token.map[0] + 1, title) if (level == 3 and chapter == "3" and number
                                                       and re.fullmatch(r"3\.\d+", number[1])) else None
            if level <= 4:
                verification = level == 4 and title == "验证关联" and feature
        elif verification and token.type == "inline":
            for clause in re.split(r"[。；;\n]", rendered_text(token)):
                if INDIRECT.search(clause):
                    continue
                for span in CASE_RANGE.finditer(clause):
                    prefix, first, last_prefix, last = span.groups()
                    if prefix == last_prefix and int(first) <= int(last):
                        ranges[prefix].append((int(first), int(last), feature, span[0]))
                for case in CASE_ID.finditer(CASE_RANGE.sub(" ", clause)):
                    explicit[case[0]][feature[0]] = feature[1]

    def candidates(ids, namespace):
        found = {}
        for case in CASE_ID.finditer(ids):
            if not case[1].endswith(f"-{namespace}-"):
                continue
            for first, last, (line, title), span in ranges.get(case[1], []):
                if first <= int(case[2]) <= last:
                    found[line] = f"{title}（区间 {span}）"
            found.update(explicit.get(case[0], {}))
        return found

    return candidates


def definition_role(template, headings, template_headings):
    """Resolve conventional feature/rule sections and surface other specific definitions for review."""
    hierarchy = [h["heading"] for h in headings if h["level"] >= 2]
    if len(hierarchy) < 2:
        return None
    numbers = [NUMBER.match(title) for title in hierarchy]
    chapter = numbers[0][1] if numbers[0] else None
    titles = [((m[2] if m else title).split("（")[0].strip()) for m, title in zip(numbers, hierarchy)]
    if titles[-1] in GENERIC or "验证关联" in titles or "功能索引" in titles:
        return None
    if template == "design-module.md" and chapter in {"7", "8", "9", "10", "11"}:
        return None
    if template == "design-index.md" and chapter == "6":
        return None
    if any(heading.split("（")[0].strip() == hierarchy[-1].split("（")[0].strip()
           for heading in template_headings):
        return None
    if template == "api-module.md":
        if chapter == "2" and len(hierarchy) == 2:
            return "definition"
    if template == "design-module.md":
        if chapter == "2" and titles[1] != "内部职责与协作":
            return "definition"
        if chapter == "3" and ((numbers[1] and numbers[1][1].startswith("3.")) or titles[1] == "共享定义"):
            return "definition"
    return "review"


def links_in(cell):
    """A link must have a displayed name. Code containing Markdown has no link nodes."""
    href = None
    result = []
    for child in cell.children:
        if child.type == "link_open":
            href = child.attrGet("href")
            named = False
        elif child.type == "link_close":
            if href and named:
                result.append(href)
            href = None
        elif href and child.content.strip() and child.type in ("text", "code_inline"):
            named = True
    return result


def group_caption(inline):
    """A caption can be a standalone link/strong label or an explicit ownership statement."""
    label = rendered_text(inline)
    if GROUP_LABEL.match(label) or label.rstrip("：:").endswith("组"):
        return True
    children = [n for n in inline.children if n.type != "text" or n.content.strip()]
    if not children or children[0].type not in ("strong_open", "link_open"):
        return False
    depth = 0
    for node in children[:-1]:
        depth += node.nesting
        if depth == 0:
            return False
    return children[-1].type == children[0].type.replace("_open", "_close")


def check_cases(tokens, classify, case_rows=None):
    if tokens is None:
        return []  # review_rendering reports the missing parser.
    tables = {t["line"]: t for t in rendered_tables(tokens)}
    candidates = reverse_cases(tokens)
    findings = []
    section = None
    heading_links = []
    caption_links = None
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            inline = tokens[i + 1]
            title = rendered_text(inline)
            if level <= 3:
                number = NUMBER.match(title)
                section = CASE_SECTIONS.get(number[1]) if level == 3 and number else None
            # Each new heading starts its own scope; an unlinked sibling cannot
            # borrow a previous group's target. A heading can own several tables.
            heading_links = links_in(inline) if section and level > 3 else []
            caption_links = None
            continue
        if section is None:
            continue
        if token.type == "paragraph_open" and token.level == 0:
            inline = tokens[i + 1]
            caption_links = links_in(inline) if group_caption(inline) else None
        elif token.type == "table_open":
            table = tables[token.map[0] + 1]
            group = heading_links if caption_links is None else caption_links
            caption_links = None  # A standalone caption applies to its own table.
            fields = table_fields(table)
            namespace, scene_field, rule_name = section
            if scene_field not in fields:
                continue
            scenario = fields.index(scene_field)
            identifier = fields.index("用例编号") if "用例编号" in fields else None
            for row in table["rows"][1:]:
                filled = [idx for idx, cell in enumerate(row) if cell.content.strip()]
                if (len(filled) == 1 and filled[0] in (identifier, scenario) and
                        group_caption(row[filled[0]])):
                    group = links_in(row[filled[0]])
                    continue
                cell = row[scenario]
                links = []
                for column, item in zip(fields, row):
                    if (column in (scene_field, "功能", "共享规则", "归属", "对应功能或共享规则") or
                            GROUP_LABEL.match(rendered_text(item))):
                        links.extend(links_in(item))
                roles = {href: classify(href) for href in dict.fromkeys(links + group)}
                reverse = candidates(rendered_text(row[identifier]), namespace) if identifier is not None else {}
                if case_rows is not None and identifier is not None:
                    case_rows.append(dict(line=cell.map[0]+1, case=rendered_text(row[identifier]),
                                          targets=list(roles), reverse=list(reverse.values())))
                valid = [(kind, owner) for kind, owner in roles.values() if kind]
                rule = rule_name + "归属待核实"
                if any(kind == "definition" for kind, _ in valid):
                    # External participants and shared rules have no local feature
                    # line. Compare the local part of an integration call chain.
                    owners = {owner for kind, owner in valid if kind == "definition" and owner is not None}
                    if not reverse or not owners or owners == set(reverse):
                        continue
                    detail = "功能落点与验证关联中的候选功能不同，按本行实际断言核对"
                elif valid:
                    detail = "落点可解析，需按场景断言核实该处是否定义对应功能或共享规则"
                else:
                    rule = rule_name + "定位"
                    detail = "测试场景或适用组头须链接到可解析的具体功能或共享规则"
                if roles:
                    detail += " · " + "、".join(roles)
                if reverse:
                    detail += " · 验证关联候选：" + "、".join(f"{name}（第 {line} 行）" for line, name in reverse.items())
                findings.append(dict(line=cell.map[0] + 1, rule=rule, detail=detail))
        elif token.level == 0 and token.nesting != -1 and token.type not in ("html_block",):
            caption_links = None
    return findings


def external_case_references(tokens, module, definition_scope):
    """A cross-module citation needs its owner's definition in the same prose block or row."""
    if tokens is None:
        return []
    findings = []

    def inspect(cells):
        hrefs = set()
        references = set()
        for cell in cells:
            for node in cell.children:
                if node.type == "link_open":
                    hrefs.add(node.attrGet("href"))
                elif node.type in ("text", "code_inline"):
                    # A test filter, source path or command is not a design-case citation.
                    if node.type == "code_inline" and not re.fullmatch(CASE, node.content):
                        continue
                    for match in CASE_ID.finditer(node.content):
                        prefix, category = match[1].rstrip("-").rsplit("-", 1)
                        if prefix != module:
                            references.add((prefix, category))
        if not references:
            return
        owners = {definition_scope(href) for href in hrefs}
        for owner, category in sorted(references - owners):
            findings.append(dict(line=cells[0].map[0]+1, rule="跨模块用例定义待核实",
                                 detail=owner+"-"+category+"：本段或本行应能定位到定义方的用例小节。"))

    row = None
    for token in tokens:
        if token.type == "tr_open":
            row = []
        elif token.type == "tr_close":
            if row:
                inspect(row)
            row = None
        elif token.type == "inline" and token.map and token.children:
            if row is None:
                inspect([token])
            else:
                row.append(token)
    return findings
