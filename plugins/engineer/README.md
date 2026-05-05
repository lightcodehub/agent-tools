# engineer

Claude Code plugin that bundles engineering execution skills, starting with `fullstack`.

## Install

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install engineer@agent-tools
```

## Use

```text
/engineer:fullstack <设计文档路径或内容>
```

## Local development

```bash
claude --plugin-dir ./plugins/engineer
```

```text
/engineer:fullstack 按这份设计文档实现用户昵称更新
```

## Included skills

- `fullstack`
  - Turn design docs into runnable, fully-tested code
  - Covers error handling, key-path logging, and test reports
  - Future: `ios`, `android`, `web`, `backend`

## Structure

```text
plugins/engineer/
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    └── fullstack/
        ├── SKILL.md
        ├── README.md
        ├── templates/
        │   ├── pre-coding-questions.md
        │   ├── implementation-checklist.md
        │   └── test-report-template.md
        └── examples/
            ├── basic.md
            └── cross-module.md
```

## Uninstall

```text
/plugin uninstall engineer
```

## More details

See `skills/fullstack/README.md` for the full skill spec and examples.
