# agent-tools

Codex / Claude Code plugin marketplace — designer 负责设计，engineer 负责实现与自测，inspector 负责独立验证与技术验收。

## Layering

| designer（设计者） | engineer（工程师） | inspector（检验员） |
| --- | --- | --- |
| `architect` 架构师：概要设计、代码架构与功能详细设计 | `developer` 开发者：实现、编写测试、自测与修复 | `validator` 验证人员：审查、执行验证、核验证据与技术验收 |

三个插件在消费项目中按角色分工。设计文档是共同依据；developer 提供自测证据，validator 重新核验并独占维护 `tests/test-report.md`。用户负责产品验收与发布决定。

正常实现请求在同一任务中衔接设计、开发和验证，设计已有且有效时直接复用。developer 交验时必须启动不继承开发对话的 validator 子 agent。用户在未参与本轮实现的干净会话中直接调用 validator，即可就地独立验收。在开发会话直接调用 validator 时，由它启动干净子代理验收。仅当用户明确只要复核时，当前会话直接检查，不更新规范报告或验收状态。仅验证不自动授权修改实现。`engineer` 另提供用户主动执行的 `discover-skills`。

## Add this marketplace

### Codex

```bash
codex plugin marketplace add lightcodehub/agent-tools
```

For local development, run this from the root of your checkout:

```bash
codex plugin marketplace add .
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
codex plugin add inspector@agent-tools
```

### Claude Code

```text
/plugin install designer@agent-tools
/plugin install engineer@agent-tools
/plugin install inspector@agent-tools
```

## Use skill

```text
/designer:architect 为订单页新增批量导出能力，先看代码再给设计文档
/engineer:developer 按这份设计文档实现昵称更新并写测试
/inspector:validator 验证本次实现是否满足设计与技术验收要求
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
├── .agents/plugins/marketplace.json
├── .claude-plugin/marketplace.json
├── plugins/
│   ├── designer/
│   │   ├── .codex-plugin/plugin.json
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/architect/
│   │   └── README.md
│   ├── engineer/
│   │   ├── .codex-plugin/plugin.json
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   │   ├── developer/
│   │   │   └── discover-skills/
│   │   └── README.md
│   └── inspector/
│       ├── .codex-plugin/plugin.json
│       ├── .claude-plugin/plugin.json
│       ├── skills/validator/
│       └── README.md
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
└── .gitignore
```

## Included plugins

- [designer](plugins/designer/README.md) — `architect`：架构设计与存量补档。
- [engineer](plugins/engineer/README.md) — `developer`：实现、自测与修复；`discover-skills`：用户主动执行的发现与注册。
- [inspector](plugins/inspector/README.md) — `validator`：代码与测试审查、独立验证、唯一报告与技术验收。

## 插件协作

模块文档以功能组织详细行为：内部职责与共享规则集中维护，接口、流程和失败边界归所属功能，测试、实施与验收通过引用衔接。规则见 [模块设计](plugins/designer/skills/architect/references/module-design.md)。

三个角色以总设计作为模块与依赖索引，按任务读取关联设计、契约和实现；接口变更或新证据触发必要扩展，不默认加载全部模块。具体规则见 [定向读取](plugins/designer/skills/architect/references/scoped-reading.md)，必要回归和独立审查要求保持不变。

完整实现与技术验收流程使用 engineer 和 inspector；需要设计或补充设计时使用 designer。inspector 可独立验证已有项目，并将设计问题和实现问题分别交给 architect 与 developer。报告模板随 inspector 分发。仓库维护不自动修改已安装插件缓存或用户注册入口。

## 测试管理约定

三个角色统一要求消费项目将测试源码按模块放在 `tests/`，测试数据与运行产物放在被忽略的 `build/tests/`。developer 仅提供本轮自测证据，validator 独占维护 `tests/test-report.md`，在其中分列 UT/IT 结果、审查发现及本次技术验收结论。

具体准入、隔离、清理与 Git 核验见 [architect 规范](plugins/designer/skills/architect/references/test-management.md)、[developer 规范](plugins/engineer/skills/developer/references/test-management.md) 和 [validator 规范](plugins/inspector/skills/validator/references/test-management.md)。三份同文规则随插件独立分发；修改时同步核对。

本仓库自身维护仅出具临时验证结果，存放于被忽略的 `build/validation/` 或受控系统临时目录，不创建根目录测试布局或规范测试报告。维护检查见 [AGENTS.md](AGENTS.md#验证)。

## 文档格式

Markdown 使用根 [.prettierrc.json](.prettierrc.json)：表格不填充列宽，普通段落不按列宽硬换行，代码块内部不重新格式化。`.prettierignore` 排除 `build/`，原始验证归档和日志不参与批量格式化。
