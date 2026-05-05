# 跨模块落地示例：订单批量导出

> 本示例演示 `/engineer:fullstack` 处理前后端联动的跨模块需求，包括后端异步任务、前端组件复用、多模块测试。

## 输入设计文档

设计文档定义：
- 后端模块：导出任务 API / 导出任务表 / 异步导出服务
- 前端模块：导出页面 / 导出按钮组件 / 进度展示组件
- 涉及数据库：`export_tasks` 表

## Step 1: 设计文档校验

| 检查项 | 结论 |
|--------|------|
| 模块拆分 | 后端 3 模块 + 前端 3 组件，边界清晰 ✅ |
| API 定义 | `POST /api/export/create` / `GET /api/export/status/:id` 完整 ✅ |
| 数据库设计 | `export_tasks` 表含字段、索引、迁移说明 ✅ |
| 前端组件来源 | 检查项目已有组件目录，进度条组件可使用 `ui/ProgressBar` ✅ |
| 测试要求 | 后端单元测试 + 前端组件测试，具体用例已定义 ✅ |

## Step 2: 合理性快速校验

- 复杂度：异步导出通过轮询查询状态，链路简单，无环形依赖 ✅
- 可扩展性：导出类型用枚举，新增类型只需新增处理器 ✅
- 潜在风险：大文件导出可能 OOM，需限制单次导出行数 ⚠️（文档未覆盖）

## Step 3: 编码前提问

```
编码前提问（1/1）：

1. [C. 边界条件缺失] 单次导出的最大行数限制是多少？超过限制是拒绝还是分片？
2. [C. 边界条件缺失] 导出任务是否需要设置 TTL 自动清理？
```

## Step 4: 后端实现

### 4.1 数据库迁移

```typescript
// migrations/20260401_create_export_tasks.ts
export async function up(db: Kysely<any>): Promise<void> {
  await db.schema
    .createTable('export_tasks')
    .addColumn('id', 'uuid', (col) => col.primaryKey().defaultTo(sql`gen_random_uuid()`))
    .addColumn('user_id', 'varchar(36)', (col) => col.notNull())
    .addColumn('type', 'varchar(50)', (col) => col.notNull())
    .addColumn('status', 'varchar(20)', (col) => col.notNull().defaultTo('pending'))
    .addColumn('params', 'jsonb', (col) => col.notNull())
    .addColumn('file_path', 'varchar(500)')
    .addColumn('error_message', 'text')
    .addColumn('created_at', 'timestamp', (col) => col.defaultTo(sql`now()`))
    .addColumn('updated_at', 'timestamp')
    .execute();

  await db.schema
    .createIndex('idx_export_tasks_user_status')
    .on('export_tasks')
    .columns(['user_id', 'status'])
    .execute();
}
```

### 4.2 创建导出 API

```typescript
// src/modules/export/export.controller.ts
async handleCreateExport(req: Request, res: Response): Promise<void> {
  const { type, params } = req.body;
  // 校验参数…
  const task = await this.exportService.createExportTask(req.userId, type, params);
  res.status(201).json({ taskId: task.id, status: task.status });
}
```

### 4.3 导出状态查询 API

```typescript
// src/modules/export/export.controller.ts
async handleGetExportStatus(req: Request, res: Response): Promise<void> {
  const task = await this.exportService.getTask(req.params.id);
  if (!task || task.user_id !== req.userId) {
    res.status(404).json({ error: '任务不存在' });
    return;
  }
  res.json({ taskId: task.id, status: task.status, progress: task.progress });
}
```

### 4.4 异步导出服务

```typescript
// src/modules/export/export.service.ts
async createExportTask(userId: string, type: string, params: Record<string, unknown>): Promise<ExportTask> {
  const rowCount = await this.estimateRowCount(type, params);
  if (rowCount > MAX_EXPORT_ROWS) {
    throw new ValidationError(`导出行数超过上限 ${MAX_EXPORT_ROWS}`);
  }
  const task = await this.exportRepository.create({ userId, type, params, status: 'pending' });
  this.queue.add(() => this.processExport(task.id));
  return task;
}
```

## Step 5: 前端实现

### 5.1 组件复用检查

按复用优先级检查：

1. **项目内已有组件**：`ui/ProgressBar` 可用，无需自研
2. **组件化工具集中存放位置**：`ui/Button` 可用
3. **开源组件**：无需引入
4. **自研实现**：仅导出页面容器需要新建

### 5.2 页面结构

```
ExportPage (新页面)
├── ExportFilters (项目已有 FilterGroup 适配)
├── ExportButton (项目已有 Button + Loading 状态)
└── ExportProgress (组合已有 ProgressBar + 状态轮询)
```

## Step 6: 测试

### 6.1 后端测试

```typescript
// src/modules/export/export.service.test.ts
describe('ExportService', () => {
  it('创建导出任务成功', async () => { /* … */ });
  it('超过行数上限时拒绝', async () => { /* … */ });
  it('查询不存在的任务返回 null', async () => { /* … */ });
});
```

### 6.2 前端组件测试

```typescript
// src/pages/export/ExportPage.test.tsx
describe('ExportPage', () => {
  it('点击导出按钮后显示进度条', async () => { /* … */ });
  it('导出完成后显示下载按钮', async () => { /* … */ });
});
```

### 6.3 运行结果

```bash
$ vitest run src/modules/export/

✓ src/modules/export/export.service.test.ts (3 tests)
✓ src/pages/export/ExportPage.test.tsx (2 tests)

Test Files  2 passed (2)
     Tests  5 passed (5)
```

## Step 7: 测试报告

测试工具 Vitest 支持 `--reporter=junit`，使用原生报告：

```bash
vitest run --reporter=junit --outputFile=reports/export-module.xml
```

报告已保存至 `reports/export-module.xml`。

## 交付摘要

- **设计文档**：订单批量导出设计文档
- **实现范围**：后端导出模块 + 前端导出页面
- **改动文件**：6 个新增 + 2 个修改
- **既有代码修改**：
  - `ui/Button` 增加 `loading` prop（与用户讨论并获得批准）
  - `ui/ProgressBar` 增加 `indeterminate` 模式（与用户讨论并获得批准）
- **测试结果**：5/5 通过
- **组件复用**：Button 和 ProgressBar 复用已有组件，仅适配新 props
- **未决问题**：
  - 导出 TTL 自动清理：已询问用户，待确认策略
