# developer

`/engineer:developer` 按设计实施、修复和重构代码，编写持久测试源码，逐单元自测后交验。该角色不限于前后端全栈；实际实现依照项目技术栈。

## 职责

- 读取本次设计和必要依赖，发现缺项进入 `/designer:architect` 补全；设计有效则直接复用。
- 阅读相关库 skill 与 API 文档，优先复用既有能力，逐单元实现、编写测试、运行并修复。
- 保留自测命令、源码/配置版本、用例与结果、退出码及原始证据；按规范管理文件和资源。
- 接收 validator 的实现或测试问题，在已授权范围内修复、自测并重新交验；改变预期先返回 architect。

代码审查、独立回归与集成验证、规范报告和技术验收由 `/inspector:validator` 负责。developer 仍须自测，不能写完代码就移交。

## 使用

```text
/engineer:developer 按这份设计文档实现用户昵称更新并写测试
/engineer:developer 修复 validator 指出的错误处理问题
```

正常端到端请求沿用原需求、scope 和授权，从 architect 到 developer 再到 validator，不要求用户重新发起任务。只要求实现阶段或 validator 不可用时，交付自测成果并明确尚未独立验收。

## 自测与交验

所有路径从消费项目根目录解析。源码固定在 `tests/{module}/unit/`、`integration/` 及实际调用的 support，数据与产物在 `build/tests/`。详细要求见 [测试管理规范](references/test-management.md)。

每轮自测先确定唯一 run-id、捕获当时源码/配置快照并配置参数实例采证，数据按模块和用例隔离。方法级结果不能替代实例证据，后续验收结果不能反填早期自测。自测摘要和原始结果放本轮 artifacts；失败、中断或未启动同样如实记录，保留 validator 尚需读取的证据并说明清理时机。

developer 不写 `tests/test-report.md`。交验传递需求、设计、scope、diff 范围、源码/配置版本、自测命令和证据路径、已知限制；旧报告不对应当前源码时明确说明。validator 对自己的运行生成唯一报告，不能将自测结果照抄为独立验证 PASS。

## 状态与完成

developer 更新模块 §9 的实施步骤、§8 用例的实际自测状态和实施时间。模块 §10 技术验收与头部完成由 validator 判定；自测通过可继续下一单元，但不代表整个模块通过验收。技术验收不代替产品验收或发布决定。

## 库能力与授权

产出可复用库或工具时，按 [skill 编写指南](references/skill-writing-guide.md) 同步真实 API 文档与轻量入口。发现与注册由用户主动执行 [discover-skills](../discover-skills/SKILL.md)，developer 不自动创建注册链接。

不擅自扩大范围、修改预期、提交、推送或发布。交验前按 [自检清单](references/checklist.md) 核对实现、自测、状态与文件准入。

## 目录

```text
skills/developer/
├── SKILL.md
├── README.md
└── references/
    ├── checklist.md
    ├── document-style.md
    ├── skill-writing-guide.md
    └── test-management.md
```

报告模板与详细结果判定随 inspector 插件分发，不在 developer 中维护另一份。

## 产出文档要求

交付的项目文档遵守 [产出文档表达规范](references/document-style.md)：直接说明有效规则、条件和依据，语言自然、精简、准确；不带对话痕迹或工作过程叙述。Markdown 表格采用紧凑格式，不填充列宽；测试报告保留必要的结果、失败原因和重试证据。

## 设计文档读取与适用性

总设计文档 §3.1 定义代码规范，§3.2 定义公共测试约定；模块 §8 以相对链接引用，并提供具体路径、命令、用例、数据准备与必要例外。既有有效设计使用其对应章节。实际接口、依赖、业务规则与测试验收信息必须完整；无适用内容的 HTTP、依赖、数据结构、数据库和 UI 子节按规则省略。

模板仅提供成品字段和可删除的填写提示。实际语言、数据库及视觉参数来自项目依据，运行时失败处理与测试替身分别定义；文档不复制角色操作规约或预填检查结论。
