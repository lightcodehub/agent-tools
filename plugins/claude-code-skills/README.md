# claude-code-skills plugin

Claude Code plugin that bundles reusable skills, starting with `program-design`.

## Install from marketplace

First add the marketplace:

```text
/plugin marketplace add lightcodehub/claude-code-skills
```

Then install this plugin:

```text
/plugin install claude-code-skills@claude-code-skills
```

After installation, use the namespaced skill command:

```text
/claude-code-skills:program-design 为订单页新增批量导出能力，先看代码再给设计文档
```

## Local development

Load the plugin locally without installing:

```bash
claude --plugin-dir ./plugins/claude-code-skills
```

Then call:

```text
/claude-code-skills:program-design 测试需求
```

## Included skills

- `program-design`
  - Read relevant code first
  - Output structured design documents
  - Require API definitions, Mermaid flowcharts, unit test design
  - Include DB design when needed
  - Prefer modular and componentized frontend design

## Plugin structure

```text
plugins/claude-code-skills/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── program-design/
│       ├── SKILL.md
│       ├── README.md
│       ├── templates/
│       └── examples/
└── README.md
```

## Uninstall

```text
/plugin uninstall claude-code-skills
```

## More details

See `skills/program-design/README.md` for the skill behavior, output contract, and examples.
