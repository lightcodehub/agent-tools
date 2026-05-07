# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`agent-tools` 是一个 Claude Code 插件 marketplace，发布到 `lightcodehub/agent-tools`。核心插件：

- **designer** — 设计类 skill 插件，目前包含 `architect`（架构设计），后续扩展 `ui`、`product`
- **engineer** — 实现类 skill 插件，目前包含 `fullstack`（全栈实现），后续扩展 `ios`、`android`、`backend`

`designer` 产出设计文档 → `engineer` 消费设计文档落地代码，形成"设计→实现"闭环。

## 目录约定

```
plugins/{plugin}/
├── .claude-plugin/plugin.json   # 插件元信息（name, version, description）
├── README.md
└── skills/{skill}/
    ├── SKILL.md                 # Claude Code 直接执行的技能规约（含 frontmatter）
    ├── README.md                # 面向用户的技能文档
    ├── templates/               # 技能引用的模板文件
    └── examples/                # 示例输入/输出
```

## SKILL.md 结构

每个 `SKILL.md` 需要 YAML frontmatter：

```yaml
---
description: 一句话描述
when_to_use: 触发条件描述
argument-hint: <参数提示>
effort: high|medium|low
allowed-tools: Read Bash(find *) Bash(grep *)  # 或 Read Edit Write Bash Glob Grep
---
```

正文必须包含：角色定位、适用/不适用场景、触发方式、输入、执行要求（分步）、强制规则、输出格式、完成标准、禁止事项。参考现有 `designer/architect/SKILL.md` 和 `engineer/fullstack/SKILL.md` 作为范本。

## 新增 skill 步骤

1. 在对应插件下创建 `plugins/{plugin}/skills/{skill}/` 目录
2. 编写 `SKILL.md`（frontmatter + 规约正文）
3. 编写 `README.md`（用户文档，结构和风格与同级 README 保持一致）
4. 按需添加 `templates/` 和 `examples/`
5. 更新 `plugins/{plugin}/README.md` 的 Included skills 列表和 Structure 树

## 版本号管理

插件版本号在 `plugins/{plugin}/.claude-plugin/plugin.json` 中维护。修改技能规约或模板后应递增 patch 版本号。

## README 对齐要求

`plugins/designer/README.md` 和 `plugins/engineer/README.md` 结构必须保持同步：中文描述、Install、Use（具体示例）、Local development、Included skills（已实现 + 待扩展）、Structure（展开到文件级）、Uninstall、More details。

分层计划统一在顶层 `README.md` 的 Layering 表格中维护，子 README 只做简述 + 链接指向。
