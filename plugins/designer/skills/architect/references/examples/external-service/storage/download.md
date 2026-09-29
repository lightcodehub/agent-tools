# 模块：download

> 所属服务: [文件存储服务](./index.md)
> 整理时间: 2026-05-09

## 1. 接口范围

文件存储服务提供文件下载和签名 URL 获取接口。

## 2. 接口列表

<a id="get-api-v2-download-fileid"></a>

### `GET /api/v2/download/:fileId`

**描述**: 下载文件。

**请求参数**:

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| fileId | path | string | 是   | 文件 ID |

**返回**: 文件二进制流

**错误码**: 404 文件不存在 / 401 认证失败

<a id="post-api-v2-sign-url"></a>

### `POST /api/v2/sign-url`

**描述**: 获取签名下载 URL。

**请求参数**:

| 参数      | 位置 | 类型   | 必填 | 说明                    |
| --------- | ---- | ------ | ---- | ----------------------- |
| fileId    | body | string | 是   | 文件 ID                 |
| expiresIn | body | int    | 否   | 有效期（秒），默认 3600 |

**返回**:

| 字段      | 类型   | 说明     |
| --------- | ------ | -------- |
| signedUrl | string | 签名 URL |
| expiresAt | string | 过期时间 |
