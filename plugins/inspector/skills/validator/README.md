# validator

`/inspector:validator` 是技术验证角色：审查本次代码与测试，独立执行验证，核验文件准入和证据，给出技术验收结论。

## 使用

```text
/inspector:validator 验证本次实现是否满足 design-doc/index.md 的要求
/inspector:validator 审查本次变更并运行回归与设计要求的集成测试
/inspector:validator 只审查指定模块，说明未执行验证的限制
```

既可接 developer 的交验，也可直接验证已有实现。缺少设计仍可完成有依据的检查，但不能猜测验收标准或宣称技术验收通过。

## 分工与边界

| 角色 | 职责 |
| --- | --- |
| architect | 定义行为预期、用例与验收标准；处理设计缺项 |
| developer | 编写实现和持久测试源码、逐单元自测、修复问题 |
| validator | 审查、独立运行验证、核验证据与文件准入、维护唯一报告及技术验收状态 |

验证不修改业务代码、持久测试、预期或验收标准。仅验证请求不自动授权修复；原任务已包含实现时可在同一任务返回相应角色处理后复验。代码审查限本次范围和必要调用链，不默认扩展为全仓重构或全面安全审计。

独立验证要求重新核对与执行，不意味着一定换了执行者；报告如实记录上下文，不能虚称多人复核。技术验收不代替用户的产品验收和发布决定。

## 报告与结果

唯一规范报告为 `tests/test-report.md`，由 validator 整体重建。UT/IT 分别统计，历史与负向验证单列，另列审查发现及本次技术验收。审查和验收不另建报告文件。

- PASS：本次要求均有充分证据，无阻断问题。
- FAIL：存在已确认的阻断缺陷、验收失败或文件准入违规。
- INCOMPLETE：无已知阻断失败，但必要审查、执行、设计或证据不足。

测试通过不自动等于技术验收通过；项目类别统计也不替代本次 scope 判定。失败、中断或阻塞仍写真实报告；用户明确只读时只在聊天交付并说明报告未更新。

## 目录

```text
skills/validator/
├── SKILL.md
├── README.md
├── assets/
│   ├── test-report.md
│   ├── unit-test-report.md
│   └── integration-test-report.md
└── references/
    ├── checklist.md
    ├── reporting.md
    └── test-management.md
```

执行时读取 [测试管理规范](references/test-management.md)、[报告规则](references/reporting.md) 和 [报告骨架](assets/test-report.md)，交付前使用 [自检清单](references/checklist.md)。所有运行资源遵守 build/tests 布局、隔离与清理规则。
