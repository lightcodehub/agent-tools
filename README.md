# agent-tools

Claude Code plugin marketplace.

## Add this marketplace

```text
/plugin marketplace add lightcodehub/agent-tools
```

## Install plugin

```text
/plugin install architect@agent-tools
```

## Use skill

```text
/architect:program 为订单页新增批量导出能力，先看代码再给设计文档
```

## Structure

```text
agent-tools/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── architect/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── program/
│       └── README.md
├── README.md
├── LICENSE
└── .gitignore
```

## Included plugins

- `architect` — includes the `program` skill

See `plugins/architect/README.md` for details.
