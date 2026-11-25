"""Compare the opening metadata block with its template and its parent document."""
import re
from urllib.parse import unquote, urlsplit

from rendered_literals import rendered_text


def title_of(tokens):
    titles = [rendered_text(tokens[i + 1]).strip() for i, t in enumerate(tokens or ())
              if t.type == "heading_open" and t.tag == "h1" and t.level == 0]
    return titles[0] if len(titles) == 1 else ""


def header_fields(tokens):
    fields = []
    quote = False
    started = False
    for t in tokens or ():
        if t.type == "heading_close" and t.tag == "h1":
            started = True
            continue
        if not started:
            continue
        if t.type == "html_block" and t.content.lstrip().startswith("<!--"):
            continue
        if t.type == "blockquote_open" and t.level == 0:
            quote = True
        elif t.type == "blockquote_close" and t.level == 0:
            quote = False
        elif not quote:
            break
        elif t.type == "inline" and t.map:
            line = t.map[0] + 1
            nodes = []
            for child in t.children:
                if child.type in ("softbreak", "hardbreak"):
                    fields.append((line, nodes))
                    nodes = []
                    line += 1
                else:
                    nodes.append(child)
            fields.append((line, nodes))
    result = []
    for line, nodes in fields:
        visible = "".join(n.content for n in nodes if n.type in ("text", "text_special", "code_inline"))
        label, _, value = re.split(r"([:：])", visible, maxsplit=1) if re.search("[:：]", visible) else ("", "", visible)
        result.append((line, label.strip(), value.strip(), nodes))
    return result


def header_schema(tokens):
    # Optional entries are declared in the template's own value placeholder.
    return [(name, "省略" in value) for _, name, value, _ in header_fields(tokens)]


def check_header(file, root, tokens, spec, parent_title):
    if tokens is None or not spec:
        return []
    findings = []

    def note(line, detail):
        findings.append(dict(line=line, rule="文件头", detail=detail))

    if not title_of(tokens):
        note(1, "缺少唯一且非空的文档一级标题")
    fields = header_fields(tokens)
    names = [f[1] for f in fields]
    expected = [name for name, optional in spec["header_fields"] if not optional or name in names]
    if names != expected:
        note(fields[0][0] if fields else 1, "引用块的字段和顺序应为 " + "、".join(expected)
             + "；实际为 " + ("、".join(n or "未命名" for n in names) or "无"))
    for line, name, value, nodes in fields:
        if not value:
            note(line, name + " 缺少值")
        if name not in ("所属设计", "所属服务"):
            continue
        parent = root / "index.md" if name == "所属设计" else file.parent / "index.md"
        title = parent_title(parent)
        if name == "所属服务":
            title = re.sub(r"\s*—\s*服务总览$", "", title).strip()
        if not title:
            note(line, name + " 无法从归属文档读取唯一标题")
        elif value != title:
            note(line, name + "应显示「" + title + "」；实际为「" + value + "」")
        links = [i for i, n in enumerate(nodes) if n.type == "link_open"]
        if len(links) != 1:
            note(line, name + " 应为一个指向归属文档的 Markdown 链接")
            continue
        i = links[0]
        uri = urlsplit(nodes[i].attrGet("href") or "")
        text = []
        for n in nodes[i+1:]:
            if n.type == "link_close":
                break
            if n.type in ("text", "text_special", "code_inline"):
                text.append(n.content)
        path = unquote(uri.path)
        if ("".join(text) != value or uri.scheme or uri.netloc or uri.query or uri.fragment or
                not path or path.startswith("/") or (file.parent / path).resolve() != parent):
            note(line, name + " 完整名称须以相对路径链接到归属文档首页")
    return findings
