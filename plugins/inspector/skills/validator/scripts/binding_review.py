"""Locate candidate caller-side evidence for indexed dependencies, regardless of language."""
from pathlib import Path
from posixpath import normpath
import re
from urllib.parse import unquote, urlsplit


def dependency_rows(docs):
    for filename, doc in docs.items():
        if doc['template'] != 'design-module.md':
            continue
        for row in doc['contracts']:
            if re.match(r'^1\.1(?:\s|[.、])', row['section']) and len(row['fields']) == 3:
                targets = list({link['href']: link for link in row['links']
                                if '](' + link['href'] + ')' in row['fields'][2]}.values())
                yield filename, row, targets


def source_texts(project, locations):
    """Use only the production paths the reviewer identified for this consumer."""
    texts = {}
    for location in locations:
        source = (project / location).resolve()
        if not source.exists() or not source.is_relative_to(project) or source == project:
            raise ValueError('expected a specific consumer path within the project: ' + location)
        candidates = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in candidates:
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(source):
                continue
            try:
                raw = path.read_bytes()
                if b'\x00' not in raw:
                    texts[str(path.relative_to(project))] = raw.decode('utf-8').splitlines()
            except UnicodeDecodeError:
                continue
    return texts


def binding_items(docs, project, paths):
    by_module = {}
    for arg in paths:
        module, sep, location = arg.partition('=')
        if not sep or not location or module + '/index.md' not in docs:
            raise ValueError('expected an inventoried module and production path: MODULE=PATH')
        by_module.setdefault(module, []).append(location)
    sources = {m: source_texts(project, ps) for m, ps in by_module.items()}
    entries = list(dependency_rows(docs))
    providers = {}
    for filename, _, targets in entries:
        for link in targets:
            provider, sym = provider_symbol(filename, link)
            if sym:
                providers.setdefault(provider, set()).add(sym)
    for filename, row, targets in entries:
        module = Path(filename).parent.name
        target_info = []
        for link in targets:
            provider, symbol = provider_symbol(filename, link)
            info = dict(label=link['label'], href=link['href'])
            if module in sources and symbol:
                hits = symbol_hits(sources[module], symbol)
                info['caller_candidates'] = hits
                if not hits:
                    info['review'] = '当前使用方路径未定位到所列符号，追查装配、别名、转发和实际使用的同提供方定义'
                    info['other_provider_candidates'] = {
                        name: evidence for name in sorted(providers[provider] - {symbol})
                        if (evidence := symbol_hits(sources[module], name))}
            target_info.append(info)
        yield dict(id=f"{filename}:{row['line']}:契约行", module=module,
                   purpose=row['fields'][1], targets=target_info)


def provider_symbol(filename, link):
    url = urlsplit(link['href'])
    path = normpath(str(Path(filename).parent / unquote(url.path))) if url.path else filename
    label = link['label'].strip('` ').split('(')[0]
    name = re.search(r'([^\W\d]\w*)$', label)
    return path, name[1] if name else ''


def symbol_hits(sources, symbol):
    pattern = re.compile(r'(?<!\w)' + re.escape(symbol) + r'(?!\w)')
    hits = []
    for filename, lines in sources.items():
        for n, line in enumerate(lines, 1):
            if pattern.search(line):
                hits.append(f'{filename}:{n}')
                if len(hits) == 3:
                    return hits
    return hits
