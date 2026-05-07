# designer

设计类 skill 插件，目前包含架构设计，后续扩展 UI 设计、产品设计等。分层计划见顶层 [README](../../README.md#layering)。

## Install

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

- `architect` — 架构设计：先读代码，再输出结构化设计文档（API、流程图、DB 设计、组件设计、测试设计）
- `ui` — 待扩展：UI/视觉设计
- `product` — 待扩展：产品设计

## Structure

```text
plugins/designer/
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    └── architect/
        ├── SKILL.md
        ├── README.md
        ├── templates/
        │   ├── design-doc.md
        │   └── checklist.md
        └── examples/
            ├── basic.md
            └── cross-module.md
```

## Uninstall

```text
/plugin uninstall designer
```

## More details

详见 [skills/architect/README.md](skills/architect/README.md)。
