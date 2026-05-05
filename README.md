# agent-tools

Claude Code plugin marketplace.

## Add this marketplace

```text
/plugin marketplace add lightcodehub/agent-tools
```

## Install plugin

```text
/plugin install architect@agent-tools
/plugin install engineer@agent-tools
```

## Use skill

```text
/architect:program 为订单页新增批量导出能力，先看代码再给设计文档
/engineer:fullstack 按这份设计文档实现昵称更新并写测试
```

## Structure

```text
agent-tools/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── architect/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── skills/
│   │   │   └── program/
│   │   └── README.md
│   └── engineer/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── fullstack/
│       └── README.md
├── README.md
├── LICENSE
└── .gitignore
```

## Included plugins

- `architect` — includes the `program` skill (read code → output design doc)
- `engineer` — includes the `fullstack` skill (implement design doc → runnable code + test report)

See `plugins/architect/README.md` and `plugins/engineer/README.md` for details.
