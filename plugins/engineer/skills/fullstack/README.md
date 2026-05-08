# fullstack

`/engineer:fullstack` 是一个按设计文档落地实现代码的 skill。

它的目标是把设计文档精确转化为可编译/可运行的实现代码，覆盖异常处理、关键路径日志、单元测试和测试报告。它不替代架构师做设计，但可在落地过程中对设计做合理性校验。

## 什么时候用

适合这些场景：

- 已有一份设计文档（`/designer:architect` 输出或手写），需要按文档写代码
- 跨模块改造经过设计阶段，需严格按方案执行
- 希望确保实现与设计文档的 API、数据结构、测试用例一致

不适合这些场景：

- 无设计文档的小修小补
- 纯讨论，没有代码上下文
- 用户只需要伪代码或思路

## 这个 skill 会做什么

触发后，它会按固定顺序工作：

1. 读取并校验设计文档完整性（支持模块化 `designs/index.md` + 各模块文档）
2. 对设计做快速合理性检查
3. 识别缺失信息并追问（最多两轮）
4. 按模块依赖图拓扑序逐模块实现代码
5. 即时写测试并运行，每完成一个模块同步更新总文档整体状态
6. 产出测试报告
7. 自检后交付（含跨模块集成点检查）
8. 如果产出了可复用库/工具，编写能力描述和对应的 skill

## 这个 skill 不会做什么

- 不无设计文档直接编码
- 不跳过测试或推迟到最后统一补
- 不擅自修改设计文档以外的模块
- 不写伪代码或留 TODO 占位
- 不自动 commit / push / 创建 PR
- 不经批准不修改既有代码

## 与 designer:architect 的协同

```mermaid
flowchart LR
    A[用户需求] --> B["/designer:architect"]
    B --> C[设计文档]
    C --> D["/engineer:fullstack"]
    D --> E[可运行代码 + 测试]
    D -.未决问题/文档缺陷.-> B
```

先用 `/designer:architect` 产出设计文档，再用 `/engineer:fullstack` 落地实现，形成完整的"设计→实现"闭环。

## 使用示例

### 示例 1：单模块后端实现

```text
/engineer:fullstack 按这份设计文档实现用户昵称更新能力
```

预期执行顺序：
- 读设计文档 → 追问未决问题（昵称是否唯一、字符集范围） → 实现 controller/service/repository → 补 Vitest 测试 → 运行测试 → 产出测试报告

### 示例 2：前后端联动需求

```text
/engineer:fullstack 执行这份订单批量导出设计文档
```

预期执行顺序：
- 读设计文档 → 检查前后端模块拆分 → 实现后端任务 API + 表迁移 → 实现前端组件 → 分别补测试 → 运行测试 → 产出测试报告

## 强约束

### 设计文档是强制前置条件
没有设计文档不得编码。如果用户没有提供，必须要求先提供或先用 `/designer:architect` 生成。

### 既有代码修改需批准
涉及修改已有代码，必须先说明原因、影响范围和风险，与用户讨论并获批准后才能动手。

### 测试与实现成对交付
每完成一个独立单元就立即写测试并运行，测试通过才进入下一单元。

### 测试报告优先使用工具原生能力
先检查测试工具是否支持内置报告输出（如 Vitest 的 `--reporter=junit`），不支持时才使用自定义模板。

## 目录结构

```text
skills/fullstack/
├── SKILL.md
├── README.md
├── templates/
│   ├── pre-coding-questions.md
│   ├── implementation-checklist.md
│   ├── test-report-template.md
│   └── skill-writing-template.md
└── examples/
    ├── basic.md
    └── cross-module.md
```

## 文件说明

- `SKILL.md`
  - 给 Claude Code 直接执行的规约
- `templates/pre-coding-questions.md`
  - 编码前提问的标准模板
- `templates/implementation-checklist.md`
  - 交付前自检清单
- `templates/test-report-template.md`
  - 自定义测试报告模板（仅测试工具无内置报告能力时使用）
- `templates/skill-writing-template.md`
  - 库/工具能力描述模板，产出可复用库/工具时使用
- `examples/basic.md`
  - 单模块实现示例
- `examples/cross-module.md`
  - 跨模块实现示例

## 产出质量判断标准

一个合格的输出，至少要满足：

- 设计文档每个章节都有对应落地
- 代码可编译/可运行
- API 签名与文档一致
- 数据结构字段与文档一致
- 每单元都有测试且已通过
- 测试报告已产出
- 未决问题与文档偏差已回报
