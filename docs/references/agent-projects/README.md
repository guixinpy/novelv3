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
| openclaw | https://github.com/openclaw/openclaw | `main` | `aa2a5c96f69a1be639c602649d4aa2e4de8da0a8` |
| hermes-agent | https://github.com/nousresearch/hermes-agent | `main` | `e078c8c6ef9bf739257404d35a9a935a1720c893` |
| openhuman | https://github.com/tinyhumansai/openhuman | `main` | `43cc1b47464f2f37a2c6b0b1a315020b0cef3131` |

下载日期：2026-08-01（2026-06-11 旧快照已替换）

> 目录已于 2026-08-01 从 `docs/archive/references/` 移出到 `docs/references/`
> （后续长期作为活跃参考使用；`docs/claude-guide/08-learning-absorption.md`
> 的 `references/agent-projects/` 引用即指向本目录。第一轮提炼稿
> `docs/archive/claude-guide-legacy/07-reference-takeaways.md` 已归档）。

## 后续使用方式

后续长期 goal 中，应优先拆解这些项目的：

- 长期记忆结构
- Agent 工具调用与编排
- 任务/计划/反思循环
- 上下文压缩与召回策略
- 用户偏好、项目记忆、程序性记忆的边界

拆解结果应沉淀为 novelv3 自己的设计文档，而不是直接照搬这些项目的通用架构。
