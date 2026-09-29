# agent-tools

Codex / Claude Code plugin marketplace — `designer` 负责设计，`engineer` 负责实现，形成完整的"设计→实现"闭环。

## Layering

| designer                     | engineer                         |
| ---------------------------- | -------------------------------- |
| `architect` 架构设计         | `fullstack` 全栈实现             |
| `ui` UI 设计（待扩展）       | `ios` iOS 实现（待扩展）         |
| `product` 产品设计（待扩展） | `android` Android 实现（待扩展） |
| ...                          | `backend` 后端实现（待扩展）     |
|                              | ...                              |

`designer` 统一收敛所有设计角色，`engineer` 统一收敛所有实现角色。两者抽象层级对等，设计文档是 designer 产出、engineer 消费的中间契约。

## Add this marketplace

### Codex

```bash
codex plugin marketplace add lightcodehub/agent-tools
```

For local development from this checkout:

```bash
codex plugin marketplace add /Users/xiaoming/Desktop/ss/agent-tools
```

### Claude Code

```text
/plugin marketplace add lightcodehub/agent-tools
```

## Install plugin

### Codex

```bash
codex plugin add designer@agent-tools
codex plugin add engineer@agent-tools
```

### Claude Code

```text
/plugin install designer@agent-tools
/plugin install engineer@agent-tools
```

## Use skill

```text
/designer:architect 为订单页新增批量导出能力，先看代码再给设计文档
/engineer:fullstack 按这份设计文档实现昵称更新并写测试
/engineer:discover-skills /path/to/project both
```

## Structure

Skill 合规以 [Agent Skills 标准协议](https://agentskills.io/specification) 为依据；宿主扩展另按 [Claude Code 文档](https://code.claude.com/docs/en/skills#frontmatter-reference) 和 [Codex 文档](https://learn.chatgpt.com/docs/build-skills) 核对。

- 包中必须有 `SKILL.md`，包含合法 YAML frontmatter 和 Markdown 正文；通用字段为 `name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`，其中前两项必填。
- 本仓库支持 Codex 和 Claude Code，共享 skill 保留 `when_to_use`、`argument-hint`、`effort` 等有实际用途的 Claude Code 扩展，并独立校验通用字段与宿主扩展。触发条件和参数说明也保留在 description 与正文中。2026-09-28 用 Codex CLI 0.154.0 的 `skills/list` 实测，这三个字段同时存在时仍正常加载、启用且无加载错误；这不等于 Codex 实现了它们的 Claude Code 配置语义，也不保证所有上传平台都接受额外字段。
- `assets/`、`references/`、`scripts/` 是推荐的资源分类；自定义目录也被协议允许。本仓库用 `assets/` 放生成物模板，`references/` 放规则、检查清单和示例。
- 协议校验、宿主兼容性、资源引用和执行流程一致性分别检查。`quick_validate.py` 的固定字段白名单会拒绝上述宿主扩展，不能把这种报错当作目标宿主不兼容的证据。仅在某个分发入口明确拒绝额外字段时为该入口适配，不为迁就校验器而删除共享源文件中的平台能力。

```text
agent-tools/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── designer/
│   │   ├── .codex-plugin/
│   │   │   └── plugin.json
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── skills/
│   │   │   └── architect/
│   │   └── README.md
│   └── engineer/
│       ├── .codex-plugin/
│       │   └── plugin.json
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   ├── fullstack/
│       │   └── discover-skills/
│       └── README.md
├── README.md
├── AGENTS.md                 # 共用的仓库维护约定，Codex 原生读取
├── CLAUDE.md                 # Claude Code 入口，引用 AGENTS.md
├── LICENSE
└── .gitignore
```

## Included plugins

- `designer` — 目前包含 `architect`（架构设计），后续扩展 `ui`、`product` 等
- `engineer` — 包含 `fullstack`（全栈实现）和 `discover-skills`（用户主动执行的项目 skill 发现与注册），后续扩展 `ios`、`android`、`backend` 等

插件详情见 [plugins/designer/README.md](plugins/designer/README.md) 和 [plugins/engineer/README.md](plugins/engineer/README.md)。
