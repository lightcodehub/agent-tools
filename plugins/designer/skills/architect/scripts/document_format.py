"""Check repeatable design-template fields against each Markdown object."""
import re
from urllib.parse import unquote, urlsplit

from read_section import sections

CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
INLINE_LINK = re.compile(r"!?\[(?:\\.|[^\[\]]|\[[^\]]*\])*\]\((?:\\.|[^()]|\([^()]*\))*\)")
OPTION = re.compile(r"(?<![\w-])--[A-Za-z][A-Za-z0-9-]*(?![A-Za-z0-9_-])", re.ASCII)
SYMBOL = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[_.][A-Za-z][A-Za-z0-9_]*)+|(?:[./]|[A-Za-z])[-.A-Za-z0-9_/]*/[A-Za-z0-9_./-]+")
REFERENCE = re.compile(r"!?\[([^\]\n]+)\](?:\[([^\]\n]*)\])?")
SECTION = re.compile(r"§\s*\d+(?:\.\d+)*")
FIELD = re.compile(r"^\s*\*\*([^*]+?)\*\*\s*[:：]\s*(.*)$")
GENERIC = re.compile(r"^(?:3\.\d+\s+)?(?:函数[/／]方法接口|函数接口|方法接口)$")


PROJECT_PATH = re.compile(r"(?<![A-Za-z0-9/_.-])(?:[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z][A-Za-z0-9]*(?![A-Za-z0-9_/.-])")


def project_file_references(visible, file, root, link):
    """Find concrete project files for classification by purpose, independent of stack."""
    project = root.parent
    findings = []
    for n, line in visible.items():
        targets = set()
        for match in link.finditer(line):
            url = urlsplit(match[2])
            if url.path and not (url.scheme or url.netloc):
                targets.add(file.parent / unquote(url.path))
        for path in PROJECT_PATH.findall(INLINE_LINK.sub(" ", line)):
            targets.add(project / path)
        identified = set()
        for target in targets:
            path = target.resolve()
            if path.is_relative_to(project) and not path.is_relative_to(root):
                rel = path.relative_to(project)
                if rel.parts and rel.parts[0] not in ("tests", "build") and path.suffix.lower() != ".md" and path.is_file():
                    identified.add(str(rel))
        if identified:
            findings.append(dict(line=n, rule="项目文件用途", detail="、".join(sorted(identified))))
    return findings


def field_issues(visible, start, end, expected):
    fields = []
    for n in range(start + 1, end + 1):
        match = FIELD.match(visible.get(n, ""))
        if match:
            fields.append((n, match[1], match[2]))
    selected = [name for _, name, _ in fields if name in expected]
    if selected != expected:
        return "字段及顺序应为 " + "、".join(expected)
    for index, (n, name, value) in enumerate(fields):
        if name not in expected or value.strip():
            continue
        until = fields[index + 1][0] if index + 1 < len(fields) else end + 1
        if not any(visible.get(i, "").strip() for i in range(n + 1, until)):
            return name + "缺少内容"
    return None


def check_objects(text, visible, template, tables):
    findings = []

    def flag(line, rule, detail):
        findings.append(dict(line=line, rule=rule, detail=detail))

    # Repeated, distinctive literals are recognizable without a language-specific dictionary.
    declared = {code[2] for line in visible.values() for code in CODE.finditer(line)
                if SYMBOL.fullmatch(code[2])}
    token = re.compile(r"(?<![A-Za-z0-9_./-])(?:" +
                       "|".join(map(re.escape, sorted(declared, key=len, reverse=True))) +
                       r")(?![A-Za-z0-9_/.-])") if declared else None
    reference_ids = {m[1].casefold() for line in visible.values()
                     if (m := re.match(r"^ {0,3}\[([^\]]+)\]:\s*\S", line))}
    for n, line in visible.items():
        if re.match(r"^\s*(?:<a\s|\[[^\]]+\]:)", line):
            continue
        prose = INLINE_LINK.sub(" ", line)
        prose = REFERENCE.sub(lambda m: " " if (m[2] or m[1]).casefold() in reference_ids else m[0], prose)
        prose = CODE.sub(" ", prose)
        literals = set(OPTION.findall(prose))
        if token:
            literals.update(token.findall(prose))
        for literal in sorted(literals):
            flag(n, "字面值", literal)
        for match in SECTION.finditer(prose):
            suffix = prose[match.end():].lstrip()
            prefix = prose[:match.start()].rstrip()
            if (not suffix or suffix[0] in "。，；、|）)") and not prefix.endswith(("》", "」", "”")):
                flag(n, "章节引用", match[0] + " 缺少章节标题")

    if template not in ("design-module.md", "api-module.md"):
        return findings
    try:
        heads = sections(text.splitlines(keepends=True))
    except ValueError as error:
        flag(1, "需解析器核实", str(error))
        return findings

    level = "3" if template == "design-module.md" else "2"
    section = next((h for h in heads if h["level"] == 2 and
                    re.match(rf"^{level}(?:[.、]\s*|\s+)", h["heading"])), None)
    if section is None:
        flag(1, "缺失章节", "第 " + level + " 节")
        return findings
    children = [h for h in heads if section["start"] < h["start"] <= section["end"]]
    direct = [h for h in children if h["level"] == 3]
    if template == "api-module.md":
        if not direct:
            flag(section["start"], "接口定义", "未定位到逐操作的接口定义")
        for op in direct:
            issue = field_issues(visible, op["start"], op["end"], ["描述", "请求参数", "返回", "错误码"])
            if issue:
                flag(op["start"], "接口字段", op["heading"] + " · " + issue)
        return findings

    indexes = [t for t in tables if section["start"] < t["line"] <= section["end"]
               and t["fields"] == ["功能", "API 定义"]]
    features = [h for h in direct if h["heading"] not in ("功能索引", "共享定义")]
    if not features:
        flag(section["start"], "功能层级", "缺少编号的功能小节")
    feature_targets = {}
    for i, feature in enumerate(features, 1):
        title, n = feature["heading"], feature["start"]
        if not re.match(rf"^3\.{i}\s+\S", title) or GENERIC.fullmatch(title):
            flag(n, "功能层级", f"第 {i} 项应为 3.{i} 加行为名称，实际为 " + title)
        for anchor in [feature["anchor"], *feature["aliases"]]:
            feature_targets[anchor] = n
        sub = [h for h in children if n < h["start"] <= feature["end"] and h["level"] == 4]
        if [h["heading"] for h in sub].count("验证关联") != 1 or sub[-1]["heading"] != "验证关联":
            flag(n, "验证关联", title + " 末尾须有一个直属验证关联子节")
    indexed = set()
    for table in indexes:
        for n, row in table["rows"]:
            match = re.fullmatch(r"\[[^\]]+\]\(#([^()]+)\)", row[0]) if row else None
            target = feature_targets.get(unquote(match[1])) if match else None
            if target is None or target in indexed:
                flag(n, "功能索引", "功能名称须链接到对应的唯一功能小节")
            indexed.add(target)
            if len(row) >= 2 and not INLINE_LINK.search(row[1]):
                flag(n, "API 定义", "缺少具体定义链接")
    if len(features) > 1:
        for f in features:
            if f["start"] not in indexed:
                flag(f["start"], "功能索引", "多功能索引未覆盖 " + f["heading"])
    return findings
