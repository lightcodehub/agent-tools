# 仓库维护约定

本仓库发布 Codex / Claude Code 插件。项目介绍、安装方式和目录见 [README.md](README.md)；具体流程按需读取对应 skill，不在此重复维护：

- [architect](plugins/designer/skills/architect/SKILL.md)：设计与存量补档。
- [developer](plugins/engineer/skills/developer/SKILL.md)：按设计实施、编写测试、自测并修复。
- [validator](plugins/inspector/skills/validator/SKILL.md)：独立审查、验证、规范报告与技术验收。
- [discover-skills](plugins/engineer/skills/discover-skills/SKILL.md)：用户主动执行的 skill 发现、清理与注册。

## 修改约定

- 修改 skill 规则时，同步相关模板、checklist、示例和引用；新增 skill 时同步根目录及插件 README。
- 同一插件的 `.codex-plugin/plugin.json` 与 `.claude-plugin/plugin.json` 保持版本一致；功能新增递增 minor，修复递增 patch。两个 marketplace 的插件来源也应一致。
- 通用协议字段与宿主扩展分别检查，不因通用校验器白名单报错就删除 `when_to_use`、`argument-hint`、`effort` 等受支持扩展。
- 保留用户已有改动，不自动 commit、push、发布或更新已安装插件缓存。生成的 Python 缓存不进入版本管理。

## 验证

本仓库是 skill 文档与插件配置项目，不套用 skill 面向消费项目定义的测试目录和规范报告布局。

- 文档、配置及 skill 行为验证只出具临时结果。摘要、日志、快照和临时项目保存在被忽略的 `build/validation/{run-id}/` 或受控系统临时目录，不进入版本控制。
- 不为本仓库维护创建根目录 `tests/` 或长期保存的 `tests/test-report.md`；验证完成后在聊天中交付结论和临时结果位置。
- 现有发现与注册脚本的测试源码保留原目录，脚本改动仍执行下述回归；临时验证项目和资源在使用结束后按保留策略清理。

Markdown 使用根 `.prettierrc.json` 的紧凑格式，不填充表格列宽；`.prettierignore` 排除临时验证目录。格式化时保留正文、链接、代码块及样例值。

文档改动检查路径、章节引用及规则一致性，并运行 `git diff --check`。发现与注册脚本改动还需在仓库根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/engineer/skills/discover-skills/scripts/tests -q
```

脚本依赖见 `plugins/engineer/skills/discover-skills/scripts/requirements.txt`。
