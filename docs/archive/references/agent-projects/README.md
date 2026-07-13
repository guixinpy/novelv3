# Agent 参考项目源码快照

本目录用于本地保存外部 Agent 项目的源码快照，供后续重审 novelv3 的长期记忆 Agent 架构时参考。

快照原则：

- 只作为阅读、拆解、对照设计材料。
- 不保留外部项目的 `.git` 目录，避免嵌套仓库。
- 不作为 novelv3 依赖直接引用。
- 默认不纳入 Git 追踪，避免第三方源码污染本仓库历史。

## 当前快照

| 项目 | 来源 | 分支 | 快照 commit |
| --- | --- | --- | --- |
| openclaw | https://github.com/openclaw/openclaw | `main` | `0bcabea9cccdc5e5e44416a58a810eee6e5d1d31` |
| hermes-agent | https://github.com/nousresearch/hermes-agent | `main` | `fe54960142d1e6edc9e43299c0e8889964f4e837` |
| openhuman | https://github.com/tinyhumansai/openhuman | `main` | `07e60af3bbb540df41970383ea6c0eeb7dd3fdb9` |

下载日期：2026-06-11

## 后续使用方式

后续长期 goal 中，应优先拆解这些项目的：

- 长期记忆结构
- Agent 工具调用与编排
- 任务/计划/反思循环
- 上下文压缩与召回策略
- 用户偏好、项目记忆、程序性记忆的边界

拆解结果应沉淀为 novelv3 自己的设计文档，而不是直接照搬这些项目的通用架构。
