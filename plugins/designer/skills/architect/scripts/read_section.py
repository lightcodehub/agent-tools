#!/usr/bin/env python3
"""List or read ATX Markdown sections without loading adjacent sections into output.

Uses Python 3 standard library only; never writes files. Explicit HTML anchors
immediately before an ATX heading and standalone HTML comments are supported.
Setext headings and other HTML blocks are refused; use a suitable Markdown
reader for unsupported syntax rather than guessing section boundaries.
"""
import argparse
import html
import json
from pathlib import Path
import re
import sys
import unicodedata

sys.dont_write_bytecode = True


def plain_title(text):
    text = re.sub(r"\s+#+\s*$", "", text.strip())

    def clean(part):
        part = re.sub(r"<!--.*?-->", "", part)
        if "<!--" in part:
            raise ValueError("multiline inline HTML comments are unsupported")
        part = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", part)
        part = re.sub(r"<[^>]*>", "", part)
        return html.unescape(part.replace("*", "").replace("~", ""))

    parts, end = [], 0
    for match in re.finditer(r"(`+)(.*?)\1", text):
        parts.append(clean(text[end:match.start()]))
        code = match.group(2)
        if code.startswith(" ") and code.endswith(" ") and code.strip():
            code = code[1:-1]
        parts.append(code)
        end = match.end()
    parts.append(clean(text[end:]))
    return "".join(parts).strip()


def sections(lines):
    found, used, pending = [], set(), []
    fence, comment, previous_text = None, False, False
    for index, line in enumerate(lines):
        if comment:
            if "-->" in line:
                _, tail = line.split("-->", 1)
                if tail.strip():
                    raise ValueError("content after an HTML comment block is unsupported")
                comment = False
            previous_text = False
            continue
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            chars, tail = marker.groups()
            if fence is None:
                if chars[0] == "`" and "`" in tail:
                    raise ValueError("invalid backtick fence info; section boundaries cannot be confirmed")
                fence = (chars[0], len(chars))
                pending = []
            elif chars[0] == fence[0] and len(chars) >= fence[1] and not tail.strip():
                fence = None
            previous_text = False
            continue
        if fence is not None:
            continue
        if re.match(r"^ {0,3}<!--", line):
            if "-->" in line:
                _, tail = line.split("-->", 1)
                if tail.strip():
                    raise ValueError("content after an HTML comment block is unsupported")
            else:
                comment = True
            previous_text = False
            continue
        anchor = re.fullmatch(r"\s*<a\s+(?:id|name)=[\"']([^\"']+)[\"']\s*>\s*</a>\s*", line)
        if anchor:
            pending.append(anchor.group(1))
            previous_text = False
            continue
        if re.match(r"^ {0,3}<[!/?A-Za-z]", line):
            raise ValueError("HTML blocks other than comments and heading anchors are unsupported")
        if previous_text and re.fullmatch(r" {0,3}(?:=+|-+)\s*", line):
            raise ValueError("Setext headings are unsupported; use an appropriate Markdown reader")
        heading = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$", line)
        if heading:
            title = plain_title(heading.group(2))
            base = "".join(c for c in title.lower()
                           if unicodedata.category(c)[0] in "LNM" or c in "_ -")
            base = base.replace(" ", "-")
            slug, suffix = base, 0
            while slug in used:
                suffix += 1
                slug = base + "-" + str(suffix)
            used.add(slug)
            found.append({"heading": title, "anchor": slug, "aliases": pending,
                          "level": len(heading.group(1)), "start": index + 1})
            pending = []
            previous_text = False
        elif line.strip():
            # Do not guess the extent of an inline comment spanning blocks.
            plain_title(line)
            pending = []
            previous_text = not bool(re.fullmatch(r" {0,3}(?:=+|-+)\s*", line))
        else:
            previous_text = False
    if comment:
        raise ValueError("unclosed HTML comment; section boundaries cannot be confirmed")
    for index, item in enumerate(found):
        item["end"] = next((x["start"] - 1 for x in found[index + 1:]
                            if x["level"] <= item["level"]), len(lines))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Markdown file, relative to --root")
    parser.add_argument("--root", required=True, help="Absolute project/library root")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--anchor", help="Observed heading anchor, without #")
    choice.add_argument("--heading", help="Exact heading text from the section listing")
    parser.add_argument("--max-chars", type=int, default=12000,
                        help="Output budget; oversized sections are refused, not truncated")
    args = parser.parse_args()
    root = Path(args.root).expanduser()
    if not root.is_absolute() or args.max_chars <= 0:
        parser.error("--root must be absolute and --max-chars must be positive")
    root = root.resolve()
    file = (root / args.file).resolve()
    try:
        relative = str(file.relative_to(root))
    except ValueError:
        parser.error("file is outside --root; use its owning root explicitly")
    try:
        lines = file.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as error:
        parser.error(str(error))
    try:
        index = sections(lines)
    except ValueError as error:
        parser.error(str(error))
    if not args.anchor and not args.heading:
        output = json.dumps({"file": relative, "sections": index}, ensure_ascii=False, indent=2)
    else:
        anchor = args.anchor.lstrip("#") if args.anchor else None
        matches = [x for x in index if (anchor is not None and
                   anchor in [x["anchor"]] + x["aliases"]) or
                   (args.heading is not None and x["heading"] == args.heading)]
        if len(matches) != 1:
            parser.error("selector must match exactly one section; omit it to list headings")
        item = matches[0]
        body = "".join(lines[item["start"] - 1:item["end"]])
        output = json.dumps({"file": relative, **item}, ensure_ascii=False) + "\n" + body
    if len(output) > args.max_chars:
        parser.error("output exceeds --max-chars; select a narrower heading or explicitly raise the budget")
    print(output, end="" if output.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
