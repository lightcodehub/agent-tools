# inspector

检验插件：审查实现与测试、独立执行验证、核验证据，给出技术验收结论。三角色分工见根 [README](../../README.md#layering)。

## Install

### Codex

```bash
codex plugin marketplace add lightcodehub/agent-tools
codex plugin add inspector@agent-tools
```

### Claude Code

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install inspector@agent-tools
```

## Use

```text
/inspector:validator 验证本次实现是否满足设计与技术验收要求
```

## Local development

```bash
claude --plugin-dir ./plugins/inspector
```

## Included skills

- [validator](skills/validator/SKILL.md) — 检验插件：审查实现与测试、独立执行验证、核验证据，给出技术验收结论。

## 职责边界

developer 交验必须新建不继承开发对话的 validator 子 agent；用户在干净会话直接调用 validator 时无需另建子 agent。实现与测试问题交 developer，设计缺项交 architect；验证角色不修改业务实现、持久测试、预期或验收标准。技术验收不代替用户的产品验收和发布决定。在开发会话直接调用 validator 或无法确认当前会话独立性时，validator 启动干净子代理并等待独立验收结论。用户明确只要复核时就地检查；无法隔离时说明未执行独立验收，均不写报告或状态。

## Structure

```text
plugins/inspector/
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── README.md
└── skills/validator/
    ├── SKILL.md
    ├── README.md
    ├── assets/
    │   ├── test-report.md
    │   ├── unit-test-report.md
    │   └── integration-test-report.md
    ├── scripts/
    │   └── read_section.py
    └── references/
        ├── checklist.md
        ├── coding-conventions.md
        ├── document-style.md
        ├── module-design.md
        ├── scoped-reading.md
        ├── reporting.md
        └── test-management.md
```

## Uninstall

### Codex

```bash
codex plugin remove inspector@agent-tools
```

### Claude Code

```text
/plugin uninstall inspector
```

## More details

详见 [skills/validator/README.md](skills/validator/README.md)。
