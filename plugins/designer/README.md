# designer

设计类 skill 插件，提供架构设计与存量设计补档。分层计划见顶层 [README](../../README.md#layering)。

## Install

### Codex

```bash
codex plugin marketplace add lightcodehub/agent-tools
codex plugin add designer@agent-tools
```

### Claude Code

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install designer@agent-tools
```

## Use

```text
/designer:architect 为订单页新增批量导出能力，先看代码再给设计文档
```

## Local development

```bash
claude --plugin-dir ./plugins/designer
```

```text
/designer:architect 测试需求
```

## Included skills

- `architect` — 开发设计：先读需求与代码，再输出概要设计、代码架构设计和模块功能详细设计

## 职责交接

architect 定义设计、具体用例与验收标准；[engineer:developer](../engineer/skills/developer/SKILL.md) 实现并自测；[inspector:validator](../inspector/skills/validator/SKILL.md) 独立审查、验证并维护唯一报告和技术验收结论。设计交付不等于实现完成，自测通过不等于技术验收通过。

## Structure

```text
plugins/designer/
├── .codex-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    └── architect/
        ├── SKILL.md
        ├── README.md
        ├── assets/
        │   ├── api-module.md
        │   ├── api-service.md
        │   ├── design-index.md
        │   ├── design-module.md
        │   └── visual-spec.md
        ├── scripts/
        │   └── read_section.py
        └── references/
            ├── checklist.md
            ├── coding-conventions.md
            ├── document-style.md
            ├── scoped-reading.md
            ├── test-management.md
            └── examples/
                ├── index.md
                ├── task/index.md
                ├── csv/index.md
                └── external-service/storage/
                    ├── index.md
                    ├── upload.md
                    └── download.md
```

## Uninstall

```text
/plugin uninstall designer
```

## More details

详见 [skills/architect/README.md](skills/architect/README.md)。
