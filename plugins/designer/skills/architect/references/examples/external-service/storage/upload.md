# 模块：upload

> 所属服务: [文件存储服务](./index.md)
> 整理时间: 2026-05-09

## 1. 接口范围

文件存储服务提供文件上传、分片上传接口。

## 2. 接口列表

<a id="post-api-v2-upload"></a>

### `POST /api/v2/upload`

**描述**: 上传单个文件。

**请求参数**:

| 参数     | 位置 | 类型   | 必填 | 说明             |
| -------- | ---- | ------ | ---- | ---------------- |
| file     | body | binary | 是   | 文件内容         |
| filename | body | string | 是   | 文件名           |
| size     | body | int    | 是   | 文件大小（字节） |

**返回**:

| 字段    | 类型   | 说明         |
| ------- | ------ | ------------ |
| fileId  | string | 文件 ID      |
| fileUrl | string | 文件访问 URL |

**错误码**: 400 文件过大 / 401 认证失败 / 500 内部错误

<a id="post-api-v2-upload-chunk"></a>

### `POST /api/v2/upload/chunk`

**描述**: 上传文件分片。

**请求参数**:

| 参数     | 位置 | 类型   | 必填 | 说明        |
| -------- | ---- | ------ | ---- | ----------- |
| uploadId | body | string | 是   | 上传会话 ID |
| chunk    | body | binary | 是   | 分片内容    |
| index    | body | int    | 是   | 分片序号    |

**返回**:

| 字段     | 类型   | 说明         |
| -------- | ------ | ------------ |
| uploadId | string | 上传会话 ID  |
| received | int    | 已接收分片数 |
