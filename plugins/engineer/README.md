# engineer

工程实现类 skill 插件，目前包含全栈实现，后续扩展 iOS、Android、后端等。分层计划见顶层 [README](../../README.md#layering)。

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
/engineer:fullstack 按这份设计文档实现用户昵称更新并写测试
/engineer:discover-skills /path/to/project both
```

## Local development

```bash
claude --plugin-dir ./plugins/engineer
```

```text
/engineer:fullstack 按这份设计文档实现用户昵称更新
```

## Included skills

- `fullstack` — 全栈实现：按设计文档落地可编译/可运行的代码，覆盖异常处理、关键路径日志、单元测试与测试报告
- `discover-skills` — 用户主动执行的项目 skill 清理与注册：清理失效入口并创建 Codex/Claude Code 相对链接，重复执行跳过正确链接，冲突保留并报告
- `ios` — 待扩展：iOS 实现
- `android` — 待扩展：Android 实现
- `backend` — 待扩展：后端实现

## Structure

```text
plugins/engineer/
├── .codex-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── README.md
└── skills/
    ├── fullstack/
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── assets/test-report-template.md
    │   └── references/
    │       ├── checklist.md
    │       └── skill-writing-guide.md
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

```text
/plugin uninstall engineer
```

## More details

详见 [skills/fullstack/README.md](skills/fullstack/README.md)。
