# 单模块落地示例：用户资料昵称更新

> 本示例演示 `/engineer:fullstack` 如何基于一份设计文档（来自 `/designer:architect` 的输出）逐单元实现代码并产出测试报告。

## 输入设计文档

使用 `designer/architect/examples/basic.md`（为用户资料新增昵称更新能力）作为输入。

## Step 1: 设计文档校验

检查发现：
- 模块拆分：controller → service → repository，结构清晰 ✅
- API 定义：`PATCH /api/users/profile/nickname`，参数完整 ✅
- 数据结构：`UpdateNicknameRequest` / `UserProfile`，字段完整 ✅
- 测试用例：5 条（含 happy/boundary/error），覆盖全面 ✅
- 未决问题：2 项（昵称唯一性、字符集范围）⚠️

## Step 2: 合理性快速校验

| 维度 | 评估 | 结论 |
|------|------|------|
| 复杂度 | controller → service → repository，新增一条更新链路，无环形依赖 | OK |
| 可扩展性 | nickname 字段可独立更新，不影响其他资料字段 | OK |
| 潜在风险 | 唯一索引若未处理历史脏数据，迁移可能失败 | 需确认 |

## Step 3: 编码前提问

```
编码前提问（1/1）：

根据设计文档，有 1 个信息需要在编码前提您确认：

1. [A. 需求不明确] 昵称的字符集范围是否有要求？（仅允许字母数字，或支持 Unicode/emoji？）
   注：昵称唯一性问题已在设计文档未决问题中列出，按"需唯一"处理，若有变更请指出。
```

## Step 4: 代码落地

### 4.1 Repository 层

```typescript
// src/modules/user/user.repository.ts
// 新增：updateNickname(userId: string, nickname: string): Promise<void>

async updateNickname(userId: string, nickname: string): Promise<void> {
  const result = await this.db
    .updateTable('users')
    .set({ nickname, updated_at: new Date() })
    .where('id', '=', userId)
    .executeTakeFirst();

  if (result.numAffectedRows === 0n) {
    throw new UserNotFoundError(userId);
  }
}
```

### 4.2 Service 层

```typescript
// src/modules/user/user.service.ts
// 新增：updateNickname(userId: string, nickname: string): Promise<UserProfile>

async updateNickname(userId: string, nickname: string): Promise<UserProfile> {
  const normalized = nickname.trim();
  if (normalized.length < 2 || normalized.length > 20) {
    throw new ValidationError('昵称长度需在 2-20 个字符之间');
  }
  await this.userRepository.updateNickname(userId, normalized);
  return this.getUserProfile(userId);
}
```

### 4.3 Controller 层

```typescript
// src/modules/user/user.controller.ts
// 新增：PATCH /api/users/profile/nickname

async handleUpdateNickname(req: Request, res: Response): Promise<void> {
  const { nickname } = req.body;
  if (typeof nickname !== 'string') {
    res.status(400).json({ error: 'nickname 必须是字符串' });
    return;
  }
  try {
    const profile = await this.userService.updateNickname(req.userId, nickname);
    res.json(profile);
  } catch (e) {
    if (e instanceof ValidationError) {
      res.status(400).json({ error: e.message });
    } else if (e instanceof UserNotFoundError) {
      res.status(404).json({ error: '用户不存在' });
    } else if (e instanceof UniqueConstraintError) {
      res.status(409).json({ error: '昵称已被使用' });
    } else {
      req.log.error(e, 'updateNickname failed');
      res.status(500).json({ error: '内部错误' });
    }
  }
}
```

## Step 5: 测试

### 5.1 Service 测试 — `src/modules/user/user.service.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { UserService } from './user.service';

const mockRepo = {
  updateNickname: vi.fn(),
  findById: vi.fn(),
};

const service = new UserService(mockRepo as any);

describe('UserService.updateNickname', () => {
  it('正常路径：更新成功的昵称', async () => {
    mockRepo.updateNickname.mockResolvedValueOnce(undefined);
    mockRepo.findById.mockResolvedValueOnce({ id: '1', nickname: 'tommy' });

    const result = await service.updateNickname('1', 'tommy');
    expect(result.nickname).toBe('tommy');
  });

  it('边界：最短昵称（2 字符）', async () => {
    mockRepo.updateNickname.mockResolvedValueOnce(undefined);
    mockRepo.findById.mockResolvedValueOnce({ id: '1', nickname: 'ab' });

    const result = await service.updateNickname('1', 'ab');
    expect(result.nickname).toBe('ab');
  });

  it('边界：最长昵称（20 字符）', async () => {
    mockRepo.updateNickname.mockResolvedValueOnce(undefined);
    const long = 'a'.repeat(20);
    mockRepo.findById.mockResolvedValueOnce({ id: '1', nickname: long });

    const result = await service.updateNickname('1', long);
    expect(result.nickname).toBe(long);
  });

  it('异常：用户不存在', async () => {
    mockRepo.updateNickname.mockRejectedValueOnce(new UserNotFoundError('404'));
    await expect(service.updateNickname('404', 'test')).rejects.toThrow(UserNotFoundError);
  });

  it('异常：昵称冲突', async () => {
    mockRepo.updateNickname.mockRejectedValueOnce(new UniqueConstraintError('nickname'));
    await expect(service.updateNickname('1', 'used-name')).rejects.toThrow(UniqueConstraintError);
  });
});
```

### 5.2 运行结果

```bash
$ vitest run src/modules/user/user.service.test.ts

✓ UserService.updateNickname (5)
  ✓ 正常路径：更新成功
  ✓ 边界：最短昵称（2 字符）
  ✓ 边界：最长昵称（20 字符）
  ✓ 异常：用户不存在
  ✓ 异常：昵称冲突

Test Files  1 passed (1)
     Tests  5 passed (5)
```

## Step 6: 测试报告

项目使用 Vitest，支持 `--reporter=junit` 输出。使用工具原生报告：

```bash
vitest run --reporter=junit --outputFile=reports/user-service.xml
```

报告文件已保存至 `reports/user-service.xml`。

## 交付摘要

- **设计文档**：user 模块昵称更新设计文档（basic.md）
- **实现范围**：controller / service / repository 三层
- **改动文件**：
  - `src/modules/user/user.controller.ts`（+28 行）
  - `src/modules/user/user.service.ts`（+15 行）
  - `src/modules/user/user.repository.ts`（+12 行）
  - `src/modules/user/user.service.test.ts`（新增，+35 行）
- **测试结果**：5/5 通过
- **未决问题**：
  - 昵称字符集范围：已询问用户，待确认
  - 昵称唯一索引迁移：需上线前扫描历史脏数据
