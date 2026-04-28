# architect

Claude Code plugin that bundles architecture design skills, starting with `program`.

## Install

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install architect@agent-tools
```

## Use

```text
/architect:program 为订单页新增批量导出能力，先看代码再给设计文档
```

## Local development

```bash
claude --plugin-dir ./plugins/architect
```

```text
/architect:program 测试需求
```

## Included skills

- `program`
  - Read relevant code first, then output structured design documents
  - API definitions, Mermaid flowcharts, unit test design, DB design, componentized frontend design

## Structure

```text
plugins/architect/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── program/
│       ├── SKILL.md
│       ├── README.md
│       ├── templates/
│       └── examples/
└── README.md
```

## Uninstall

```text
/plugin uninstall architect
```

## More details

See `skills/program/README.md` for the full skill spec and examples.
