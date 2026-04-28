# design-tools

Claude Code plugin that bundles design workflow skills, starting with `program-design`.

## Install

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install design-tools@agent-tools
```

## Use

```text
/design-tools:program-design 为订单页新增批量导出能力，先看代码再给设计文档
```

## Local development

```bash
claude --plugin-dir ./plugins/design-tools
```

```text
/design-tools:program-design 测试需求
```

## Included skills

- `program-design`
  - Read relevant code first, then output structured design documents
  - API definitions, Mermaid flowcharts, unit test design, DB design, componentized frontend design

## Structure

```text
plugins/design-tools/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── program-design/
│       ├── SKILL.md
│       ├── README.md
│       ├── templates/
│       └── examples/
└── README.md
```

## Uninstall

```text
/plugin uninstall design-tools
```

## More details

See `skills/program-design/README.md` for the full skill spec and examples.
