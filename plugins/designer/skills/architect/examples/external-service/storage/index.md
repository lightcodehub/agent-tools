# 文件存储服务 — 服务总览

> 整理时间: 2026-05-09
> 来源: 用户提供 OpenAPI 文档

## 服务信息

- **基础地址**: `https://storage.internal/api/v2`
- **认证方式**: API Key（Header `X-API-Key`）
- **公共请求头**: `Content-Type: application/json`

## API 模块索引

| 模块     | 职责               | 文档                         | 状态      |
| -------- | ------------------ | ---------------------------- | --------- |
| upload   | 文件上传、分片上传 | [upload.md](./upload.md)     | ⏳ 待实现 |
| download | 文件下载、签名 URL | [download.md](./download.md) | ⏳ 待实现 |

## 公共约定

| 约定项   | 说明                                                     |
| -------- | -------------------------------------------------------- |
| 错误格式 | `{ "error": { "code": "string", "message": "string" } }` |
| 超时     | 上传 30s，下载 10s                                       |
