# agent-tools

Claude Code plugin marketplace.

## Add this marketplace

```text
/plugin marketplace add lightcodehub/agent-tools
```

## Install plugin

```text
/plugin install design-tools@agent-tools
```

## Use skill

```text
/design-tools:program-design 为订单页新增批量导出能力，先看代码再给设计文档
```

## Structure

```text
agent-tools/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── design-tools/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── program-design/
│       └── README.md
├── README.md
├── LICENSE
└── .gitignore
```

## Included plugins

- `design-tools` — includes the `program-design` skill

See `plugins/design-tools/README.md` for details.
