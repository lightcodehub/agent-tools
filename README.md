# agent-tools

Claude Code plugin marketplace — `designer` 负责设计，`engineer` 负责实现，形成完整的"设计→实现"闭环。

## Layering

| designer | engineer |
| --- | --- |
| `architect` 架构设计 | `fullstack` 全栈实现 |
| `ui` UI 设计（待扩展） | `ios` iOS 实现（待扩展） |
| `product` 产品设计（待扩展） | `android` Android 实现（待扩展） |
| ... | `backend` 后端实现（待扩展） |
| | ... |

`designer` 统一收敛所有设计角色，`engineer` 统一收敛所有实现角色。两者抽象层级对等，设计文档是 designer 产出、engineer 消费的中间契约。

## Add this marketplace

```text
/plugin marketplace add lightcodehub/agent-tools
```

## Install plugin

```text
/plugin install designer@agent-tools
/plugin install engineer@agent-tools
```

## Use skill

```text
/designer:architect 为订单页新增批量导出能力，先看代码再给设计文档
/engineer:fullstack 按这份设计文档实现昵称更新并写测试
```

## Structure

```text
agent-tools/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── designer/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── skills/
│   │   │   └── architect/
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

- `designer` — 目前包含 `architect`（架构设计），后续扩展 `ui`、`product` 等
- `engineer` — 目前包含 `fullstack`（全栈实现），后续扩展 `ios`、`android`、`backend` 等

插件详情见 [plugins/designer/README.md](plugins/designer/README.md) 和 [plugins/engineer/README.md](plugins/engineer/README.md)。
