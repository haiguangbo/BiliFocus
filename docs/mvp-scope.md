# BiliFocus 项目范围

## 1. 项目目标

BiliFocus 是一个面向单用户的、本地优先的 Bilibili 内容工作台。

当前项目的目标不是做一个“站外版 Bilibili”，而是围绕下面这条链路建立稳定体验：

搜索 -> 筛选 -> 同步 -> 整理 -> 回看

用户打开它，是为了更有条理地沉淀内容，而不是继续陷在信息流里。

## 2. 核心使用场景

典型使用场景如下：

1. 用户输入一个主题、技能或学习方向
2. 系统从 Bilibili 拉取候选视频
3. 用户可追加轻量自然语言筛选，例如“只看教程”“排除直播切片”
4. 系统返回规范化结果
5. 用户将合适结果同步到本地片库
6. 用户在本地片库中继续分类、检索、回看
7. 用户在设置页管理本地偏好、Cookie 和二维码登录
8. 用户可运行“智能获取”或“结构化重写”来进一步整理本地内容

## 3. 当前页面范围

当前项目页面限定为：

- `内容探索`：搜索、筛选、同步、智能获取
- `本地片库`：本地视频浏览、分类、分页、排序
- `偏好设置`：本地偏好、Cookie、二维码登录、结构化重写
- `视频详情`：本地详情页、播放壳、流信息和元数据

额外允许一个非 Web 页面工具：

- `apps/downloader/` 下的本地 CLI 下载器

说明：

- CLI 下载器是辅助工具，不应把下载管理反向塞进主 Web UI。

## 4. 当前能力范围

当前项目可以包含以下能力：

- 真实 Bilibili Web 搜索
- 轻量规则化自然语言筛选
- 搜索结果同步到本地 SQLite
- 本地片库检索、分类浏览与分页
- 本地结构化重写
- 基于学习目标的智能获取与本地策展
- 智能获取阶段流展示与任务进度轮询
- 本地播放进度记录
- Bilibili Cookie 手动维护
- Bilibili 二维码扫码登录桥接
- 可选 LLM 增强的分类、整理与去重
- 可选 CrewAI 编排能力
- 按 `bvid` 下载视频的本地 CLI

## 5. 当前 API 范围

当前项目 API 主要包括：

- `GET /health`
- `POST /api/search`
- `POST /api/sync/search`
- `GET /api/videos`
- `GET /api/videos/{bvid}`
- `GET /api/videos/{bvid}/playback`
- `GET /api/videos/{bvid}/stream`
- `POST /api/videos/{bvid}/playback-progress`
- `POST /api/videos/{bvid}/sync`
- `POST /api/videos/{bvid}/sync-series`
- `POST /api/videos/rewrite-metadata`
- `DELETE /api/videos/{bvid}`
- `GET /api/preferences`
- `PUT /api/preferences`
- `GET /api/auth/bilibili/qrcode`
- `GET /api/auth/bilibili/qrcode/poll`
- `POST /api/curation/run`
- `POST /api/curation/jobs`
- `GET /api/curation/jobs/{job_id}`

## 6. 当前边界

以下内容不属于当前项目范围：

- 多用户数据隔离
- BiliFocus 自己的账号体系
- 独立登录页、权限页、角色页
- 评论、弹幕、社交关系、消息通知
- 创作者上传流程
- 云端部署作为前提
- 微服务拆分
- 云向量库、复杂推荐系统
- 必须依赖外部 LLM 才能运行的基础路径

说明：

- Bilibili 二维码登录只用于写入本地 Cookie，不代表项目具备自己的登录系统。

## 7. 成功标准

当前项目可以视为“范围内完成”的条件包括：

- 用户可以在 Web 页面中搜索候选视频
- 用户可以对搜索结果加轻量筛选条件
- 用户可以将候选结果同步到本地库
- 用户可以在本地片库中检索、分类和回看
- 用户可以在设置页维护偏好和 Bilibili Cookie
- 用户可以通过二维码登录桥接把 Cookie 写回本地设置
- 用户可以运行智能获取并看到后端真实任务阶段
- 用户可以对本地视频做结构化重写
- 前后端都能通过 Docker Compose 或本地脚本启动
- 文档、README、代码实现三者基本一致
