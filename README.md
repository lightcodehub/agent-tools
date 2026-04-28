# claude-code-skills marketplace

This repository is a Claude Code plugin marketplace.

## Add this marketplace

```text
/plugin marketplace add lightcodehub/claude-code-skills
```

## Install the plugin from this marketplace

```text
/plugin install claude-code-skills@claude-code-skills
```

## Use the skill

```text
/claude-code-skills:program-design 为订单页新增批量导出能力，先看代码再给设计文档
```

## Marketplace structure

```text
claude-code-skills/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── claude-code-skills/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── program-design/
│       ├── README.md
│       └── ...
├── LICENSE
└── .gitignore
```

## Included plugin

- `claude-code-skills`
  - includes the `program-design` skill

See `plugins/claude-code-skills/README.md` for plugin details.
