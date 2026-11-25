"""Find exposed command, key and example literals using rendered nodes and field roles."""
import re


COMMAND_FIELDS = {"命令", "子命令", "命令示例", "命令格式", "调用命令", "command", "subcommand", "invocation"}
KEY_FIELDS = {"按键", "快捷键", "键位", "key binding", "shortcut", "keystroke"}
EXAMPLE_FIELDS = {"输入", "输入值", "输入示例", "输出", "输出值", "操作", "操作步骤", "场景与输入", "预期", "预期输出", "预期结果", "输出示例", "断言",
                  "input", "action", "expected", "expected result", "expected output", "assertion"}
DECLARATION_FIELDS = {"参数", "参数名", "请求参数", "字段", "字段名", "返回字段", "响应字段", "选项", "参数名称", "schema type",
                      "parameter", "parameter name", "argument", "option", "field", "field name", "response field"}
PROTOCOL_FIELDS = {"错误码", "错误代码", "状态码", "返回码", "响应码", "协议状态", "响应状态", "返回值", "响应", "响应值",
                   "error code", "status code", "return code", "response code", "response status", "response", "return value"}
STATUS_FIELDS = {"状态", "status"}
MEANING_FIELDS = {"含义", "意义", "语义", "meaning"}
QUALIFIED_STATUS = re.compile(r"[a-z][a-z0-9.+-]*\s*(?:状态(?:码)?|错误码|响应码|\s+status(?: code)?)")
FIELD_CONTEXT = re.compile(r"^(?:请求参数|返回字段|响应字段|参数|(?i:parameters|response fields))\s*[:：]?$")
PROTOCOL_LABEL = re.compile(r"^(?:" + "|".join(sorted(PROTOCOL_FIELDS, key=len, reverse=True)) + r")\s*[:：]", re.I)
# Lists are matched as complete values, then projected onto exposed text. Slashes
# and list punctuation separating properly formatted literals need no correction.
MEMBER = r"(?:[+-]?[0-9][A-Za-z0-9_.-]*|[A-Za-z_][A-Za-z0-9_.-]*(?:\[\][.][A-Za-z_][A-Za-z0-9_.-]*)*)"
SEPARATOR = r"\s*(?:[/|,，、;；]|或|和|与|\bor\b|\band\b)\s*"
VALUE_LIST = re.compile(MEMBER + r"(?:" + SEPARATOR + MEMBER + r")*")
PROTOCOL_ENTRY = re.compile(r"(?:^|[:：，,;；。])\s*(?:(?:其余|其他|其它)?非\s*)?(" + VALUE_LIST.pattern +
                            r")(?=\s*(?:$|[。；;：:]|表示|代表|意味着|对应|时))")
NAME = r"[A-Za-z][A-Za-z0-9_-]*"
ATOM = r"[A-Za-z0-9_./+-]+"
COMMAND = re.compile(NAME + r"(?:[ \t]+" + ATOM + r")*")
OPTION = re.compile(r"(?<![A-Za-z0-9_/-])--?[A-Za-z][A-Za-z0-9_-]*(?:=[A-Za-z0-9_./+-]+)?")
# A code option proves the neighbouring node is part of a possible invocation even
# when the executable itself never appears in code. Keep English prose leads intact.
BEFORE_OPTION = re.compile(r"(?<![A-Za-z0-9_/-])([a-z][a-z0-9_-]*)[ \t]*$")
PROSE_CONNECTORS = {"a", "an", "and", "as", "by", "for", "in", "is", "or", "see", "the", "to", "use", "with"}
COMMAND_CUE = re.compile(r"(?:运行|执行|调用|键入|命令(?:名)?[为是：:]?|\b(?:run|execute|invoke|command)\s+)\s*$", re.I)
COMMAND_SUFFIX = re.compile(r"(?<![A-Za-z0-9_/-])([a-z][a-z0-9_-]*)\s*(?:子命令|命令(?!行|式))")
CHINESE = re.compile(r"[\u3400-\u9fff]")
KEY_NAME = (r"(?i:Enter|Return|Esc(?:ape)?|Tab|Space|Backspace|Delete|Home|End|Insert|"
            r"(?:Arrow)?(?:Left|Right|Up|Down)|Page(?:Up|Down)|F\d{1,2})")
CHORD = (r"(?:(?i:ctrl|control|alt|shift|cmd|command|meta|option|super)[+-])+"
         r"(?:" + KEY_NAME + r"|[A-Za-z0-9+/-])")
KEY = r"(?:" + CHORD + r"|" + KEY_NAME + r"|[A-Za-z0-9])"
KEY_CUE = re.compile(r"(?:按下|按键|快捷键|连按|按(?=\s*(?:[小大]写|[A-Za-z]))|\bpress\s+|\bshortcut\s+)\s*(?:[大小]写)?\s*[：:]?\s*(" + KEY + r")(?![A-Za-z0-9_-])", re.I)
CHORD_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])" + CHORD + r"(?![A-Za-z0-9_-])")
KEY_ACTION = re.compile(r"(?<![A-Za-z0-9_/-])([A-Za-z]|" + CHORD + r")\s*(?:(?:键|表示|代表|用于|请求|仍|只|仅)\s*)*(?:退出|取消|确认|返回上级|打开菜单|刷新界面)")
INTERACTION = re.compile(r"按键|键盘|终端|取消|退出|回车|快捷键|按下|敲击|\b(?:key|keyboard|press|terminal|quit)\b", re.I)
# Only local assertion context assigns semantic weight to strings like "pending".
# One-time examples can be found even in a document with no code declarations.
VALUE = r"(?:[A-Z][A-Z0-9_-]*[ \t]+(?=[+\-]?\d))?[+-]?[A-Za-z0-9_]+(?:[./:-][A-Za-z0-9_+-]+)*"
VALUE_CUE = re.compile(r"(?:显示|返回|写入|输出|输入|键入|断言|预期|期望|取值|其余|否则|等于|置为|设为|设置为|结果为|状态为|"
                       r"\b(?i:returns?|prints?|outputs?|equals?|expects?)\s+)\s*(?:应?为|应?是|包含|得到|[：:=])?\s*"
                       r"(?P<value>" + VALUE + r")(?![A-Za-z0-9_-])")
QUOTED = re.compile(r'''“([^”\n]+)”|「([^」\n]+)」|"([^"\n]+)"|(?<![A-Za-z])'([^'\n]+)'(?![A-Za-z])''')
EXAMPLE_LABEL = re.compile(r"(?:^|[。；;])\s*(?:输入|操作|断言|输出示例|预期(?:结果|输出)?|期望(?:结果|输出)?|(?i:input|action|assertion|expected(?: output| result)?))\s*[:：]")


# Exact assignments and alternatives in example cells give evidence independent of
# whether another module documents the same vocabulary.
ASSIGNMENT = re.compile(r"(?<![A-Za-z0-9_-])" + NAME + r"\s*=\s*" + VALUE)
ALTERNATIVES = re.compile(r"(?<![A-Za-z0-9_./-])[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)+(?![A-Za-z0-9_./-])")
WORD = re.compile(r"(?<![A-Za-z0-9_/-])" + NAME + r"(?![A-Za-z0-9_-])")
ARGUMENT = re.compile(r"""^(?:\s*=\s*|\s+)("[^"\n]+"|'[^'\n]+'|“[^”\n]+”|""" + ATOM +
                      r")(?=\s*[,，。；;、）)]|\s*$|[\u3400-\u9fff])")
ACTION = re.compile(r"(?:运行|执行|键入|调用|\b(?:run|execute|invoke)\s+)\s*$", re.I)
CONCEPT = re.compile(r"\s*(?:接口|协议|文档|编码|格式|模式|对象|规范|类型|数据|文件|消息|响应|请求)")


def table_roles(tokens):
    """Map inline cells to their rendered header, including formatted headers."""
    roles = {}
    headers = []
    column = 0
    in_table = False
    preceding = ""
    protocol = False
    fields = False
    for i, token in enumerate(tokens):
        if token.type == "table_open":
            headers = []
            in_table = True
            protocol = preceding.rstrip("：:").casefold() in PROTOCOL_FIELDS
            fields = bool(FIELD_CONTEXT.fullmatch(preceding))
        elif token.type == "table_close":
            in_table = False
            preceding = ""
        elif token.type == "inline" and not in_table:
            preceding = rendered_text(token).strip()
        elif token.type in ("fence", "code_block", "html_block"):
            preceding = ""
        elif token.type == "tr_open":
            column = 0
        elif token.type in ("th_open", "td_open"):
            cell = tokens[i + 1]
            if token.type == "th_open":
                headers.append(rendered_text(cell).strip().casefold())
            elif column < len(headers):
                role = headers[column]
                if role in {"类型","type"} and {"用例编号","测试场景"}.issubset(headers):
                    role = "case category"
                if role in {"类型","字段类型","参数类型","返回类型","type","data type"} and DECLARATION_FIELDS.intersection(headers):
                    role = "schema type"
                if fields and role in {"名称", "name"}:
                    role = "field"
                if QUALIFIED_STATUS.fullmatch(role) or (role in STATUS_FIELDS and (protocol or MEANING_FIELDS.intersection(headers))):
                    role = "status code"
                roles[id(cell)] = role
            column += 1
    return roles


def node_text(node):
    if node.type in ("softbreak", "hardbreak"):
        return " "
    return "" if node.type == "html_inline" else node.content


def rendered_text(token):
    return "".join(node_text(node) for node in token.children)


def split_invocation(children, index, declarations):
    """A flag and its command may both be styled yet form two separate copyable spans."""
    if index < 2 or children[index].type != "code_inline":
        return None
    space = children[index - 1]
    previous = children[index - 2]
    if space.type != "text" or not space.content.isspace() or previous.type != "code_inline":
        return None
    commands = declarations[0]
    first, following = previous.content, children[index].content
    if re.fullmatch("[A-Z]{2,12}", first) and following.startswith("/"):
        return first + " " + following
    if commands and first.split() and commands.fullmatch(first.split()[0]) and OPTION.match(following):
        return first + " " + following
    return None


def example_boundary(children, index, role):
    """Only flag joined values as potential instances in case input/result cells."""
    node = children[index]
    if role in EXAMPLE_FIELDS and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*(?:/[A-Za-z0-9_-]+)+",node.content):
        return "同一代码片段含斜杠分隔值；独立参数实例按原名分别呈现，真实单一输入保留原分隔符"
    if index and children[index-1].type == "text":
        prefix = children[index-1].content
        if re.search(r"(?<![A-Za-z0-9_])\d+\.$",prefix) and re.match(r"^\d+(?:\s*[A-Za-z]|$)",node.content):
            return "小数点与有效数字落在不同节点；核实完整显示值"
    return None


def expression_boundary(children, index):
    """Check punctuation and tokens immediately outside a rendered code node."""
    previous = children[index - 1] if index else None
    following = children[index + 1] if index + 1 < len(children) else None
    name = children[index].content
    if not re.fullmatch(r"[A-Za-z_][\w.]*", name, re.ASCII):
        return None
    if following and following.type == "text":
        tail = re.match(r"^(?:\([A-Za-z0-9_., *-]*\)(?:\.[A-Za-z_]\w*)*|\.[a-zA-Z_]\w*)", following.content, re.ASCII)
        if tail:
            return name + tail[0]
    if previous and previous.type == "text":
        path = re.search(r"(?:^|[^A-Za-z0-9_.-])((?:/[A-Za-z0-9_.-]+)*/)$", previous.content)
        if path and not (index >= 2 and previous.content == "/" and children[index-2].type == "code_inline"):
            return path[1] + name
    return None


def exposed_chords(children, context):
    """Report the whole chord when one of its key names renders as prose."""
    chords = list(CHORD_PATTERN.finditer(context))
    exposed = {}
    if chords:
        start = 0
        for index, node in enumerate(children):
            end = start + len(node_text(node))
            if node.type == "text":
                for chord in chords:
                    overlap = context[max(start, chord.start()):min(end, chord.end())]
                    if re.search(r"[A-Za-z0-9]", overlap):
                        exposed.setdefault(index, []).append(chord[0])
            start = end
    return exposed


def word_pattern(words):
    if words:
        choices = "|".join(map(re.escape, sorted(words, key=lambda w: (-len(w), w))))
        return re.compile(r"(?<![A-Za-z0-9_-])(?:" + choices + r")(?![A-Za-z0-9_-])")
    return None


def collect_declarations(token_sets):
    commands, examples, keys, symbols = set(), set(), set(), set()
    for tokens in token_sets:
        if not tokens:
            continue
        roles = table_roles(tokens)
        for t in tokens:
            if t.type != "inline" or not t.children:
                continue
            value = rendered_text(t)
            role = roles.get(id(t))
            if role in COMMAND_FIELDS and (invocation := COMMAND.fullmatch(value.strip())):
                commands.add(invocation[0].split()[0])
                examples.add(invocation[0])
            if role in KEY_FIELDS and re.fullmatch(KEY, value.strip()):
                keys.add(value.strip())
            keys.update(KEY_CUE.findall(value))
            for i, node in enumerate(t.children):
                if node.type == "code_inline":
                    # An operation heading such as METHOD /path defines a callable verb too.
                    commands.update(re.findall(r"(?<![A-Za-z0-9_-])([A-Z][A-Z0-9_-]+)\s+(?=/|<)",node.content))
                    # A simple name is significant when declared as a method, field, or qualified member.
                    # Do not treat every capitalized word in a code example as a new API name.
                    symbols.update(re.findall(r"(?:^|[.:])([A-Za-z_]\w*)\s*\(", node.content, re.ASCII))
                    symbols.update(re.findall(r"[A-Za-z_]\w*\.([A-Z][A-Za-z0-9_]*)\b", node.content, re.ASCII))
                    if role in {"字段", "字段名", "属性", "配置项", "field", "property"} and re.fullmatch(NAME, node.content):
                        symbols.add(node.content)
                    symbols.update(word for word in re.findall(r"[A-Za-z][A-Za-z0-9_]*", node.content)
                                   if re.search(r"[a-z][A-Z]", word))
                if node.type != "code_inline" or not COMMAND.fullmatch(node.content):
                    continue
                words = node.content.split()
                if (role in COMMAND_FIELDS or (i and COMMAND_CUE.search(t.children[i-1].content))
                        or (len(words) > 1 and OPTION.fullmatch(words[1]))):
                    commands.add(words[0])
                if len(words) > 1:
                    examples.add(node.content)
    names = commands | {phrase for phrase in examples if phrase.split()[0] in commands}
    return word_pattern(names), word_pattern(keys), word_pattern(symbols)


RESULT_CODES = re.compile(
    r"(?:返回(?:码|状态|值)?|响应(?:码|状态)?|退出(?:码|状态)?|错误码|"
    r"\b(?:exit(?:s| code)?|returns?|status code)\b)"
    r"\s*(?:为|是|[:：=])?\s*(-?\d+(?:\s*[/、]\s*-?\d+)*)"
    r"(?![A-Za-z0-9_.])", re.I)
CODE_NAME = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]*(?![A-Za-z0-9_])")
VALUE_CONTEXT = re.compile(r"信号|按键|组合键|变量|环境|控制位|状态码|退出码|模式位|寄存器|文件描述符|"
                           r"\b(?:signal|keystroke|environment|variable|mask|descriptor)\b", re.I)
EXPRESSION = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\([^()\n]{0,64}\)(?:\.[A-Za-z_]\w*)*",re.ASCII)


def literal_candidates(children, index, role, context, declarations):
    """Review visible text only. Preserve the source node separately in the rendered view."""
    value = children[index].content
    commands, keys, symbols = declarations
    found = OPTION.findall(value) + COMMAND_SUFFIX.findall(value) + KEY_CUE.findall(value)
    if role in COMMAND_FIELDS and COMMAND.fullmatch(value.strip()):
        found.append(value.strip())
    if role in DECLARATION_FIELDS | PROTOCOL_FIELDS | KEY_FIELDS and VALUE_LIST.fullmatch(context.strip()):
        if value.strip() == context.strip():
            found.append(value.strip())
        else:
            found.extend(word for word in re.findall(MEMBER, value) if word.casefold() not in {"or", "and"})
    elif role in PROTOCOL_FIELDS:
        entry = PROTOCOL_ENTRY.match(value)
        if entry and entry[1].casefold() not in {"or", "and"}:
            found.append(entry[1])
    elif PROTOCOL_LABEL.match(context):
        found.extend(v for v in PROTOCOL_ENTRY.findall(value) if v.casefold() not in {"or", "and"})
    found.extend(KEY_ACTION.findall(value))
    for match in CODE_NAME.finditer(value):
        word = match[0]
        if re.search(r"[a-z][A-Z]", word) or (len(word) >= 2 and word.isupper() and VALUE_CONTEXT.search(context)):
            found.append(word)
    found.extend(EXPRESSION.findall(value))
    found.extend(m[1] for m in RESULT_CODES.finditer(value))
    found.extend(re.findall(r"(?<![A-Za-z0-9_-])(?:UT|IT)\d{3}(?:/\d{3})*(?![A-Za-z0-9_])", value))
    found.extend(re.findall(r"(?<![A-Za-z0-9_.-])(?:[a-z][a-z0-9_-]*:)?[0-9]+(?:\.[0-9]+){2,}(?:-[a-zA-Z0-9_.-]+)?(?![A-Za-z0-9_.-])", value))


    if symbols and (CHINESE.search(context) or role in EXAMPLE_FIELDS or VALUE_CONTEXT.search(context)):
        found.extend(symbols.findall(value))
    for word in WORD.finditer(value):
        if not word[0].isupper() and ACTION.search(value[:word.start()]) and not CONCEPT.match(value[word.end():]):
            found.append(word[0])
    if commands:
        for match in commands.finditer(value):
            if (role in COMMAND_FIELDS or CHINESE.search(context) or match[0] == context.strip()
                    or COMMAND_CUE.search(value[:match.start()]) or OPTION.match(value[match.end():].lstrip())):
                found.append(match[0])
    if keys and (role in KEY_FIELDS | EXAMPLE_FIELDS or INTERACTION.search(context)):
        found.extend(keys.findall(value))
    if role in KEY_FIELDS and re.fullmatch(KEY, value.strip()):
        found.append(value.strip())
    after = children[index + 1] if index + 1 < len(children) else None
    if after and after.type == "code_inline" and OPTION.match(after.content):
        match = BEFORE_OPTION.search(value)
        if (match and match[1] not in PROSE_CONNECTORS and
                (role in COMMAND_FIELDS or CHINESE.search(value) or match[1] == value.strip()
                 or COMMAND_CUE.search(value[:match.start()]))):
            found.append(match[1])
    before = children[index - 1] if index else None
    if before and before.type == "code_inline" and (match := ARGUMENT.match(value)):
        invocation = before.content.strip()
        if (match[1].casefold() not in PROSE_CONNECTORS and
                (OPTION.fullmatch(invocation) or (commands and commands.fullmatch(invocation)))):
            found.append(match[1].rstrip("."))
    label = EXAMPLE_LABEL.search(context)
    if role in EXAMPLE_FIELDS or label:
        found.extend(m["value"] for m in VALUE_CUE.finditer(value) if not CONCEPT.match(value[m.end():]))
        found.extend(ASSIGNMENT.findall(value))
        found.extend(ALTERNATIVES.findall(value))
        for quote in QUOTED.finditer(value):
            if (quote[0] == value.strip() or label or
                    re.search(r"显示|输出|返回|匹配|输入|断言|期望|预期|表头|列名|文案|回显|日志", value[max(0, quote.start()-10):quote.start()])):
                found.append(next(s for s in quote.groups() if s))
        if label:
            sample = context[label.end():].strip().rstrip("。；;")
            if re.fullmatch(VALUE, sample) and sample in value:
                found.append(sample)
        if re.fullmatch(VALUE, context.strip()) and value.strip() == context.strip():
            found.append(value.strip())
    return list(dict.fromkeys(found))
