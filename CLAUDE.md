# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`agent-tools` 是一个 Claude Code 插件 marketplace，发布到 `lightcodehub/agent-tools`。核心插件：

- **designer／1.1.0** — 设计类 skill 插件，包含 `architect`（架构设计），后续扩展 `ui`、`product`
- **engineer／1.1.0** — 实现类 skill 插件，包含 `fullstack`（全栈实现），后续扩展 `ios`、`android`、`backend`

`designer` 产出模块化设计文档（`design-doc/`） → `engineer` 消费设计文档落地代码，形成"设计→实现"闭环。

## 核心设计

### 设计文档结构

designer:architect 输出到项目根目录 `design-doc/`，结构如下（详见对应 SKILL.md）：

```
design-doc/
├── index.md                     ← 总设计文档（背景/范围/代码规范/视觉规范/模块索引/风险/跨模块未决问题）
├── {module-name}/
│   └── index.md                 ← 模块文档（概述/流程/API/数据/DB/用户交互/影响面/测试/实施计划/验收/未决问题）
└── external-service/            ← 跨项目外部服务依赖
    └── {name}/
        ├── index.md             ← 服务总览
        └── {module}.md          ← API 模块（锚点索引）
```

- 模块按业务逻辑划分，不以技术分层（controller/service/repository）为边界
- 模块间依赖通过相对链接引用，共享数据结构在定义方模块文档中定义
- 外部服务依赖使用 `external-service/{name}/`，API 以 `{#method-path}` 为锚点，模块 §1.3 按行索引
- 循环依赖检测：DFS 有向图，有环则拒绝输出

### 状态追踪

所有可实施条目均有状态列，使用全文字格式：

- `⏳ 待实现`（初始）→ `🔄 待迭代`（设计变更）→ `🧪 待测试`（实现完）→ `✅ 已完成`（测试通过）
- 状态更新附带时间戳 `(YYYY-MM-DD)`，designer 写"设计时间"，engineer 写"实施时间"
- 追踪粒度：模块索引表（总览）→ 实施计划每步 → 测试用例每行 → 验收标准每项
- 视觉规范也跟踪状态

### 用户交互设计

- 设计侧：先询问用户是否有设计稿/原型稿；无则调研布局/交互/参考产品，确认后绘制线框图写入模块 §6
- 实现侧：组件优先级 项目内已有 > 开源 > 自研，遵守总文档视觉规范（色值表+语义映射+亮暗模式）
- 色值/字体/间距/圆角/阴影全部封装为常量，禁止硬编码

## 目录约定

```
plugins/{plugin}/
├── .claude-plugin/plugin.json   # 插件元信息（name, version, description）
├── README.md
└── skills/{skill}/
    ├── SKILL.md                 # Claude Code 直接执行的技能规约（含 frontmatter）
    ├── README.md                # 面向用户的技能文档
    ├── templates/               # 技能引用的模板文件
    └── examples/                # designer 有示例输出（目录结构），engineer 无
```

## SKILL.md 结构

YAML frontmatter：

```yaml
---
description: 一句话描述
when_to_use: 触发条件描述
argument-hint: <参数提示>
effort: high|medium|low
allowed-tools: Read Bash(find *) Bash(grep *) # 或 Read Edit Write Bash Glob Grep
---
```

正文：角色定位、适用/不适用场景、触发方式、输入、执行要求（分步）、强制规则、输出格式、完成标准、禁止事项。

## 新增 skill 步骤

1. 在对应插件下创建 `plugins/{plugin}/skills/{skill}/` 目录
2. 编写 `SKILL.md`（frontmatter + 规约正文）和 `README.md`
3. 按需添加 `templates/` 和 `examples/`
4. 更新 `plugins/{plugin}/README.md` 的 Included skills 和 Structure 树

## 版本号管理

`plugins/{plugin}/.claude-plugin/plugin.json` 中维护。修改规约或模板后递增版本号。

## 格式规范

- 所有 markdown 使用 prettier 风格：表格列对齐、列表缩进一致、空行分隔、代码块标注语言
- Mermaid 语法：特殊字符/中文用 `ID["标签"]` 格式，禁止裸写
- Blockquote 多行之间用空 `>` 换行
- 状态值必含文字（`⏳ 待实现` 而非纯 `⏳`）
- 日期格式统一 `YYYY-MM-DD`
