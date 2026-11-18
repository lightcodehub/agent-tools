# engineer

工程实现插件：编写业务代码与测试、逐单元自测、修复问题并交验。三角色分工见根 [README](../../README.md#layering)。

## Install

### Codex

```bash
codex plugin marketplace add lightcodehub/agent-tools
codex plugin add engineer@agent-tools
```

### Claude Code

```text
/plugin marketplace add lightcodehub/agent-tools
/plugin install engineer@agent-tools
```

## Use

```text
/engineer:developer 按这份设计实现用户昵称更新并写测试
```

## Local development

```bash
claude --plugin-dir ./plugins/engineer
```

## Included skills

- [developer](skills/developer/SKILL.md) — 工程实现插件：编写业务代码与测试、逐单元自测、修复问题并交验。
- [discover-skills](skills/discover-skills/SKILL.md) — 用户主动执行的 skill 发现、清理与注册；使用 `/engineer:discover-skills /path/to/project both`。

## 职责边界

developer 负责自测并保留本轮证据。正式交验时，新建不继承开发对话的 `/inspector:validator` 子代理，由它审查、执行验证并维护唯一报告。无法隔离时交付已有成果，注明“未执行独立验收”；同一上下文复核不能代替独立验收。

当前开发入口为 `/engineer:developer`。插件安装与项目 skill 注册由用户管理，仓库维护不自动修改已安装缓存或用户注册链接。

## Structure

```text
plugins/engineer/
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    ├── developer/
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── scripts/
    │   │   └── read_section.py
    │   └── references/
    │       ├── checklist.md
    │       ├── coding-conventions.md
    │       ├── document-style.md
    │       ├── module-design.md
    │       ├── scoped-reading.md
    │       ├── self-test.md
    │       ├── skill-writing-guide.md
    │       └── test-management.md
    └── discover-skills/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/usage.md
        └── scripts/
            ├── scan_skills.py
            ├── register_skills.py
            ├── requirements.txt
            └── tests/
                ├── test_scan_skills.py
                └── test_register_skills.py
```

## Uninstall

### Codex

```bash
codex plugin remove engineer@agent-tools
```

### Claude Code

```text
/plugin uninstall engineer
```

## More details

详见 [skills/developer/README.md](skills/developer/README.md)。
