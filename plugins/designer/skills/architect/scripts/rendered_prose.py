"""Read the GFM inline nodes actually rendered in paragraphs, headings and table cells."""
import re
from urllib.parse import unquote, urlsplit

from rendered_literals import example_boundary, expression_boundary, split_invocation
from rendered_literals import collect_declarations, exposed_chords, literal_candidates, rendered_text, table_roles

try:
    from markdown_it import MarkdownIt
except ImportError:
    MarkdownIt = None


TICKS = re.compile(r"`+")
LINK_SYNTAX = re.compile(r"\[[^\]\n]+\]\(")
# Strong/emphasis is valid Markdown; these are review candidates, not automatic rewrites.
IDENTIFIER = re.compile(r"[^\W\d]\w*\Z")
TECHNICAL = r"(?:--?[\w-]+|[\w./:-]+)"
JOINED = re.compile(TECHNICAL + r"\s+(?:与|和|或|以及|versus|rather than)\s+" + TECHNICAL, re.I)


# Distinctive spellings can be reviewed even when every occurrence was left unformatted.
TECHNICAL_TEXT = re.compile(
    r"(?<![A-Za-z0-9_])(?:[a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+|"
    r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*-(?:UT|IT)-[0-9]+|"
    r"[A-Za-z][A-Za-z0-9_-]*(?:\.[a-zA-Z][a-zA-Z0-9_-]*)+|"
    r"(?<![A-Za-z0-9_-])-[a-zA-Z](?![a-zA-Z0-9_-])|"
    r"[a-zA-Z][a-zA-Z0-9]*(?=\s*(?:字段|参数名|配置项名)))(?![A-Za-z0-9_])"
)


def rendered_tables(tokens):
    tables = []
    for i, token in enumerate(tokens):
        if token.type == "table_open":
            tables.append({"line": token.map[0] + 1, "rows": []})
        elif token.type == "tr_open":
            tables[-1]["rows"].append([])
        elif token.type in ("td_open", "th_open"):
            tables[-1]["rows"][-1].append(tokens[i + 1])
    return tables


def table_fields(table):
    return ["".join(n.content for n in cell.children) for cell in table["rows"][0]]


def template_rendering(tokens, spec):
    """Apply the installed template's fields to tables and links in the rendered tree."""
    kind = spec.get("name")
    if kind not in ("design-index.md", "design-module.md", "api-module.md", "api-service.md"):
        return []
    tables = rendered_tables(tokens)
    models = spec["tables"]
    heads = [(int(t.tag[1:]), tokens[i + 1].content, t.map[0] + 1)
             for i, t in enumerate(tokens) if t.type == "heading_open"]
    findings = []
    for i, (level, title, start) in enumerate(heads):
        end = next((n for lv, _, n in heads[i + 1:] if lv <= level), float("inf"))
        local = [t for t in tables if start < t["line"] < end]
        key = title.partition(" ")[0].rstrip(".、")
        required = spec.get("fixed_labels", {}).get(key, [])
        if required:
            labels = {m[1] for t in tokens if t.type == "inline" and t.map and start < t.map[0] + 1 < end
                      if (m := re.match(r"^\*\*([^*]+)\*\*\s*[:：]", t.content))}
            for label in required:
                if label not in labels:
                    findings.append(dict(line=start, rule="模板字段待核实", detail=title + " · " + label))
        if kind == "design-module.md" and key == "4":
            expected = next((m["fields"] for m in models if m["fields"][:2] == ["字段","类型"]), None)
            for table in local:
                fields = table_fields(table)
                if expected and fields[:2] == ["字段","类型"] and fields != expected:
                    findings.append(dict(line=table["line"], rule="数据结构字段表", detail="、".join(expected)))
                if fields and fields[0] == "类型" and any("字段" in col for col in fields[1:]):
                    for row in table["rows"][1:]:
                        cell = row[0]
                        if not any(n.type == "code_inline" for n in cell.children):
                            continue
                        if not any(n.type == "link_open" for n in cell.children):
                            findings.append(dict(line=cell.map[0]+1, rule="结构定义定位待核实",
                                detail=rendered_text(cell) + "：类型索引须能找到实际声明、规范字段表或已维护的共享定义。"))
        if kind == "design-module.md" and key == "6":
            required_ui = ["组件与复用", "界面与状态"]
            for label in required_ui:
                if label in spec.get("headings",[]) and not any(
                        depth == level+1 and child == label and start < n < end for depth,child,n in heads):
                    findings.append(dict(line=start,rule="界面模板小节待核实",detail=label))
        if kind == "design-module.md" and key == "8.2":
            accepted = set(spec.get("case_types", []))
            for table in local:
                fields = table_fields(table)
                if not accepted or "类型" not in fields or "测试场景" not in fields:
                    continue
                for row in table["rows"][1:]:
                    cell = row[fields.index("类型")]
                    value = rendered_text(cell).strip()
                    if value and not set(re.split(r"\s*[/／、]\s*", value)) <= accepted:
                        findings.append(dict(line=cell.map[0]+1,rule="用例类型待核实",
                                             detail=value + " · 按模板分类，专项验证维度保留在场景说明中"))
        if kind == "api-module.md" and level == 3:
            findings.extend(protocol_tables(tokens, local, models, start, end))
        if kind == "design-module.md" and level == 2 and key in ("9","10"):
            column = "实施内容" if key == "9" else "验收条件"
            for table in local:
                fields = table_fields(table)
                if column not in fields:
                    continue
                for row in table["rows"][1:]:
                    cell = row[fields.index(column)]
                    fragments = [unquote(urlsplit(n.attrGet("href")).fragment) for n in cell.children
                                 if n.type == "link_open"]
                    if not any(f and not re.match(r"^(?:[1-9][-、]|10-验收|11-未决)", f) for f in fragments):
                        findings.append(dict(line=cell.map[0]+1, rule=column+"定位待核实",
                                             detail=column+"应定位具体设计；公共准备、模块回归或跨模块交付按实际对象核实。"))
        if ((kind == "design-module.md" and title.startswith("8.4 ")) or
                (kind == "api-service.md" and title == "公共约定")):
            prefix = title.split()[0]
            expected = next((t["fields"] for t in models if t["section"] and t["section"][-1].startswith(prefix)), None)
            if expected and not any(table_fields(t) == expected for t in local):
                findings.append(dict(line=start, rule="已启用章节的模板表待核实",
                                     detail=title + " · " + "、".join(expected)))
    return findings


def protocol_tables(tokens, tables, models, start, end):
    fields = []
    for t in tokens:
        if t.type == "inline" and t.map and start < t.map[0] + 1 < end:
            label = re.match(r"^\*\*([^*]+)\*\*\s*[:：]", t.content)
            if label:
                fields.append((label[1], t))
    findings = []
    for i, (label, token) in enumerate(fields):
        key = {"请求参数": "参数", "返回": "字段"}.get(label)
        if not key:
            continue
        expected = next((m["fields"] for m in models if m["fields"][0] == key), None)
        line = token.map[0] + 1
        limit = fields[i + 1][1].map[0] + 1 if i + 1 < len(fields) else end
        actual = [table_fields(t) for t in tables if line < t["line"] < limit]
        structured = re.search(r"字段|对象|payload|object", token.content, re.I) and any(
            n.type == "code_inline" for n in token.children)
        if expected and expected not in actual and (actual or structured):
            findings.append(dict(line=line, rule="协议字段表待核实", detail=label + " · " + "、".join(expected)
                                 + "；标量、无正文或公共定义引用按真实契约核实。"))
    return findings


def parse_tokens(text):
    if MarkdownIt is None:
        return None
    # Keep escapes and entities distinct from raw punctuation. Table cell maps
    # identify the original row in the same tree used for all following checks.
    parser = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"]).disable("text_join")
    return parser.parse(text)


def review_rendering(text, include_nodes=False, project_names=(), spec=None, tokens=None, declarations=None):
    if MarkdownIt is None:
        return {"parser": None, "blocks": 0}, [dict(
            line=1, rule="正文渲染未核验",
            detail="当前 Python 未提供 markdown-it-py。使用已具备该包的解释器重跑，或用项目 GFM 渲染器逐文件对照成稿。")], []

    if tokens is None:
        tokens = parse_tokens(text)
    if declarations is None:
        declarations = collect_declarations([tokens])
    roles = table_roles(tokens)
    names = re.compile(r"(?<![a-zA-Z0-9_])(?:" + "|".join(map(re.escape, project_names)) +
                       r")(?![a-zA-Z0-9_])") if project_names else None
    findings, blocks = template_rendering(tokens, spec or {}), []
    block_count = 0
    cell = 0
    for t in tokens:
        if t.type == "tr_open":
            cell = 0
        elif t.type in ("th_open", "td_open"):
            cell += 1
        elif t.type == "tr_close":
            cell = 0
        if t.type != "inline" or not t.map or not t.children:
            continue
        block_count += 1
        start = line = t.map[0] + 1
        nodes = []
        in_link = False
        html_code_depth = 0
        children = t.children
        role = roles.get(id(t))
        context = rendered_text(t)
        chords = exposed_chords(children, context)
        for i, child in enumerate(children):
            kind, value = child.type, child.content
            if kind == "link_open":
                in_link = True
            elif kind == "link_close":
                in_link = False
            if kind == "html_inline":
                if re.match(r"<(?:code|kbd)(?:\s[^>]*|)>$", value, re.I):
                    html_code_depth += 1
                elif re.match(r"</(?:code|kbd)\s*>$", value, re.I):
                    html_code_depth = max(0, html_code_depth - 1)
            reason = ""
            if kind == "code_inline":
                if role == "case category" and any(n.type == "text" and re.search(r"\w", n.content) for n in children):
                    reason = "用例类型分类名的普通文字与代码节点混排；按同一分类标签核实"
                elif (sample_issue := example_boundary(children, i, role)):
                    reason = sample_issue
                elif (invocation := split_invocation(children, i, declarations)):
                    reason = "命令与紧随的参数分成两个代码节点；核实是完整调用还是分别解释元素"
                    value = invocation
                elif (expression := expression_boundary(children, i)):
                    reason = "调用、字段或路径只有一部分落入代码节点，结合上下文核实边界"
                    value = expression
                elif any(len(m[0]) >= len(child.markup) for m in TICKS.finditer(value)):
                    reason = "代码内仍显示同宽或更长的反引号"
                elif LINK_SYNTAX.search(value):
                    reason = "链接语法被呈现为代码"
                elif JOINED.search(value):
                    reason = "同一代码片段包含多个由正文连接的技术值"
            elif kind == "text" and not html_code_depth:
                if TICKS.search(value):
                    reason = "反引号落在普通正文中"
                elif LINK_SYNTAX.search(value):
                    reason = "链接语法落在普通正文中"
                elif not in_link:
                    literals = literal_candidates(children, i, role, context, declarations)
                    literals.extend(chords.get(i, ()))
                    symbols = TECHNICAL_TEXT.findall(value) + (names.findall(value) if names else [])
                    if literals or symbols:
                        reason = "字面值或声明名显示为普通文本，按实际用途核实"
                        value = "、".join(dict.fromkeys(literals + symbols))
                if not reason and "**" in value:
                    reason = "双星号落在普通正文中，核实强调或字面值边界"
            elif kind in ("strong_open", "em_open") and child.markup.startswith("_"):
                if i + 2 < len(children) and children[i + 2].type == kind.replace("_open", "_close"):
                    value = children[i + 1].content
                    if IDENTIFIER.fullmatch(value):
                        reason = "标识符形状的文本被强调，外围下划线未显示"
            if reason:
                findings.append(dict(line=line, rule="正文渲染边界", detail=(
                    (f"第 {cell} 列 · " if cell else "") + reason + " · " + kind + " " + repr(value))))
            if include_nodes:
                if kind == "link_open":
                    value = child.attrGet("href") or ""
                elif kind == "image":
                    value = child.attrGet("src") or ""
                nodes.append([kind, value if kind in ("link_open", "image") else child.content])
            if kind in ("softbreak", "hardbreak"):
                line += 1
            elif kind == "code_inline" and t.map[1] > start and "\n" in t.content and value not in t.content:
                # CommonMark replaces code-span newlines with spaces. Report the
                # containing source block when subsequent inline offsets are ambiguous.
                line = start
        if include_nodes:
            blocks.append(dict(line=start, end=t.map[1], column=cell or None, nodes=nodes))
    return dict(parser="markdown-it-py (CommonMark + tables + strikethrough)", blocks=block_count), findings, blocks
