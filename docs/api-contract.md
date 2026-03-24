# BiliFocus API 契约

本文档描述当前项目对外使用的主要 API 形状。任何共享请求或响应结构变更，都应先更新本文档，再改实现。

## 1. 通用约定

- 所有响应使用 JSON
- 时间字段统一使用 ISO 8601 UTC 字符串
- 当前项目不包含用户 ID、租户 ID、多用户上下文
- `bvid` 是所有视频相关接口中的稳定外部标识
- provider 原始字段不应直接泄漏到 API 响应

## 2. 健康检查

### `GET /health`

用途：

- 本地健康检查
- Docker readiness

响应示例：

```json
{
  "status": "ok",
  "app": "bilifocus-backend",
  "version": "0.1.0"
}
```

## 3. 搜索与同步

### `POST /api/search`

用途：

- 根据关键词和可选筛选文本，从 provider 拉取候选视频

请求体示例：

```json
{
  "query": "fastapi",
  "filter_text": "只看教程，排除直播切片",
  "limit": 20,
  "offset": 0,
  "source": "default"
}
```

响应要点：

- 返回标准化 `items`
- 每条视频至少包含 `bvid`、`title`、`author_name`、`tags`、`cached`
- 返回 `total`、`limit`、`offset`

### `POST /api/sync/search`

用途：

- 将一批搜索结果同步到本地 SQLite

请求体与 `POST /api/search` 基本一致。

响应示例：

```json
{
  "job_id": "sync_search_20260324_001",
  "status": "completed",
  "query": "fastapi",
  "saved_count": 6,
  "skipped_count": 2,
  "failed_count": 0,
  "started_at": "2026-03-24T10:00:00Z",
  "finished_at": "2026-03-24T10:00:02Z"
}
```

## 4. 智能获取

### `POST /api/curation/run`

用途：

- 同步执行一次完整的智能获取流程，并在接口返回时附带最终结果

请求体示例：

```json
{
  "objective": "围绕 AI Agent、系统设计和工程化实践，筛选适合长期学习的视频",
  "extra_requirements": "不要短视频，不要标题党，不要直播切片",
  "max_keywords": 5,
  "limit_per_keyword": 6,
  "sync_accepted": true
}
```

响应字段要点：

- `recommended_keywords`
- `pipeline_trace`
- `reviewed_count`
- `accepted_count`
- `saved_count`
- `accepted_items`

### `POST /api/curation/jobs`

用途：

- 创建一个异步智能获取任务，并立即返回任务信息

响应示例：

```json
{
  "job_id": "curation_agent_1",
  "status": "queued",
  "stage": "planner",
  "progress_message": "任务已创建，等待执行"
}
```

### `GET /api/curation/jobs/{job_id}`

用途：

- 查询异步智能获取任务的运行状态和最终结果

响应示例：

```json
{
  "job_id": "curation_agent_1",
  "status": "running",
  "stage": "collector",
  "progress_message": "正在从 Bilibili 拉取候选视频",
  "result": null,
  "error_message": null
}
```

完成后的响应示例：

```json
{
  "job_id": "curation_agent_1",
  "status": "completed",
  "stage": "completed",
  "progress_message": "AI 策展执行完成",
  "result": {
    "job_id": "curation_agent_1",
    "status": "completed",
    "objective": "围绕 AI Agent、系统设计和工程化实践，筛选适合长期学习的视频",
    "recommended_keywords": ["Agent 系统设计", "RAG 工程化", "大模型实战"],
    "pipeline_trace": {
      "planner": {
        "agent": "volcengine.keyword_planner",
        "status": "fallback",
        "summary": "未启用 CrewAI planner，改用 volcengine adapter 生成了 3 个关键词",
        "outputs": ["Agent 系统设计", "RAG 工程化", "大模型实战"]
      },
      "reviewer": {
        "agent": "local.content_reviewer",
        "status": "fallback",
        "summary": "未启用 CrewAI reviewer，使用本地硬规则完成审核",
        "outputs": ["保留 6 条", "拒绝 10 条"]
      },
      "classifier": {
        "agent": "local.content_classifier",
        "status": "fallback",
        "summary": "未启用 CrewAI classifier，使用本地启发式标签",
        "outputs": ["已处理 6 条通过项"]
      }
    },
    "reviewed_count": 16,
    "accepted_count": 6,
    "rejected_count": 10,
    "saved_count": 6,
    "skipped_count": 0,
    "accepted_items": [],
    "started_at": "2026-03-24T10:00:00Z",
    "finished_at": "2026-03-24T10:00:05Z"
  },
  "error_message": null
}
```

当前前端应依赖 `stage` 和 `progress_message` 展示实时流程，而不是自行猜测阶段。

## 5. 本地视频与播放

### `GET /api/videos`

用途：

- 读取本地 SQLite 中的视频列表

支持的常见查询参数：

- `q`
- `tag`
- `sort`
- `limit`
- `offset`

### `GET /api/videos/{bvid}`

用途：

- 获取本地视频详情

### `POST /api/videos/{bvid}/sync`

用途：

- 按单个 `bvid` 拉取并同步到本地

### `POST /api/videos/{bvid}/sync-series`

用途：

- 以当前视频为入口扩展同步系列内容

### `DELETE /api/videos/{bvid}`

用途：

- 从本地库删除一条视频记录

### `GET /api/videos/{bvid}/playback`

用途：

- 获取本地播放器可用的播放地址和清晰度列表

### `GET /api/videos/{bvid}/stream`

用途：

- 通过后端代理视频字节流

### `POST /api/videos/{bvid}/playback-progress`

用途：

- 保存本地播放进度

请求体示例：

```json
{
  "position_seconds": 128.4,
  "duration_seconds": 1420,
  "completed": false
}
```

## 6. 本地结构化重写

### `POST /api/videos/rewrite-metadata`

用途：

- 对本地视频进行结构化重写，补充摘要、标签和学习焦点

请求体示例：

```json
{
  "limit": 20,
  "tag": "英语提升"
}
```

响应示例：

```json
{
  "job_id": "rewrite_metadata_20260324_001",
  "status": "completed",
  "rewritten_count": 12,
  "skipped_count": 3,
  "updated_bvids": ["BV1xx411c7mD"],
  "started_at": "2026-03-24T10:00:00Z",
  "finished_at": "2026-03-24T10:00:12Z"
}
```

## 7. 偏好设置

### `GET /api/preferences`

用途：

- 读取本地单用户偏好

### `PUT /api/preferences`

用途：

- 更新本地偏好

核心字段包括：

- `default_search_limit`
- `default_source`
- `default_filter_text`
- `bilibili_cookie`
- `download_output_dir`
- `library_sort`

说明：

- `bilibili_cookie` 是本地敏感数据，只用于上游请求增强，不代表平台账号体系。

## 8. Bilibili 二维码登录桥接

### `GET /api/auth/bilibili/qrcode`

用途：

- 创建一次本地二维码登录会话

响应示例：

```json
{
  "status": "pending",
  "qrcode_key": "abc123",
  "login_url": "https://passport.bilibili.com/...",
  "expires_in_seconds": 180
}
```

### `GET /api/auth/bilibili/qrcode/poll`

用途：

- 轮询二维码登录状态

查询参数：

- `qrcode_key`

响应示例：

```json
{
  "status": "completed",
  "state": "confirmed",
  "message": "扫码登录成功，已写入本地 Cookie",
  "cookie_configured": true
}
```

说明：

- 登录成功后，后端会把 Cookie 写入本地偏好
- 前端应刷新设置并回填当前 Cookie 节点
- 这不是 BiliFocus 自己的登录系统
