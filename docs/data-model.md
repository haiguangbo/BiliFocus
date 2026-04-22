# BiliFocus 数据模型说明

本文档说明当前项目中稳定的数据对象、持久化字段和本地存储边界。

## 1. 总体原则

- 所有持久化数据默认存放在本地 SQLite
- 核心视频对象必须保持稳定，避免前后端各自发散
- provider 原始字段不能直接暴露到 API
- 少量补充元数据可以进入 `raw_extra`，但必须受控

## 2. 核心对象

### 2.1 `VideoItem`

用于搜索结果、本地列表和智能获取结果展示。

核心字段：

- `bvid`：Bilibili 视频唯一标识
- `title`：标题
- `author_name`：作者名
- `cover_url`：封面地址
- `duration_seconds`：时长
- `published_at`：发布时间
- `view_count`：播放量
- `like_count`：点赞数
- `summary`：归一化摘要
- `tags`：标签数组
- `primary_category`：一级分类
- `secondary_category`：二级分类
- `series_key`：系列键
- `series_title`：系列标题
- `playback_position_seconds`：本地播放位置
- `playback_progress_percent`：本地播放进度
- `playback_last_played_at`：最近播放时间
- `playback_completed`：是否看完
- `match_reasons`：命中原因
- `cached`：是否已存在于本地库

### 2.2 `VideoDetail`

在 `VideoItem` 基础上扩展本地详情页所需字段。

附加字段：

- `description`
- `source_url`
- `sync_status`
- `last_synced_at`
- `raw_extra`

### 2.3 `PreferenceConfig`

表示单用户本地偏好设置。

主要字段：

- `default_search_limit`
- `default_source`
- `default_filter_text`
- `bilibili_cookie`
- `download_output_dir`
- `theme`
- `language`
- `library_sort`
- `hide_watched_placeholder`

说明：

- `bilibili_cookie` 属于本地敏感数据，不应提交到代码仓库。

### 2.4 `PipelineStageTrace`

表示智能获取某个阶段的最终摘要。

字段：

- `agent`
- `status`
- `summary`
- `outputs`

### 2.5 `CurationJobStatus`

表示智能获取异步任务的运行状态。

字段：

- `job_id`
- `status`：`queued` / `running` / `completed` / `failed`
- `stage`：`planner` / `collector` / `reviewer` / `classifier` / `sync` / `completed`
- `progress_message`
- `result`

## 3. `raw_extra` 的允许内容

`raw_extra` 只用于承载小规模、受控、非核心但对体验有帮助的信息。

允许进入的内容包括：

- 播放流相关信息
- 结构化重写结果
- 本地播放状态补充字段
- 分类与系列信息
- 分 P / 剧集树等序列化数据

不应进入的内容包括：

- 大块 provider 原始响应
- 无边界扩张的实验字段
- 临时调试结果

## 4. SQLite 持久化原则

- 所有时间字段统一使用 ISO 8601 UTC 字符串
- 视频主记录按 `bvid` 去重
- 同步与更新优先采取 upsert 思路
- 播放进度属于本地状态，允许直接回写视频相关记录
- 偏好设置是单例记录，不需要多用户设计

## 5. 本地敏感数据

以下数据允许本地存储，但不应提交到远程仓库：

- `bilibili_cookie`
- 下载文件
- 本地数据库
- CrewAI 运行痕迹
- 本地日志或中间状态

## 6. 模型演进规则

涉及以下内容变更时，必须先更新本文档：

- 新增或删除持久化字段
- 修改 upsert 规则
- 修改播放状态写回方式
- 修改偏好设置结构
- 修改 `raw_extra` 的边界
