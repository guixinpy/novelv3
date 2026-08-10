# Claude 开发指导文档集（claude-guide）

本目录是项目方向的**权威文档集**：只放「现状、方向、规则、决策、活跃设计」，
不含已完成阶段的历史与过程记录（归档于 `../archive/claude-guide-legacy/`）。

每次开发 session 开始时，按以下顺序阅读：

1. **`00-backend-architecture.md`** —— 后端架构总览（现状，必读）
2. **`01-vision.md`** —— 项目定位与北极星目标
3. **`04-development-rules.md`** —— 开发规则（测试纪律/依赖方向/协作约束）
4. 其余文档按需查阅

## 文档清单

| 文档 | 内容 | 更新频率 |
| --- | --- | --- |
| `00-backend-architecture.md` | 后端架构总览：三层分层、模块职责、数据流、数据表 | 架构变化时 |
| `01-vision.md` | 项目重新定义：novelv3 是什么、不是什么、北极星目标 | 方向变化时 |
| `04-development-rules.md` | 开发规则：测试纪律、依赖方向、验证命令、文档纪律 | 规则变化时 |
| `06-decisions.md` | 架构决策记录（ADR，CADR-001 起） | 决策时 |
| `08-learning-absorption.md` | 三开源项目学习吸收定稿（hermes/openhuman/openclaw） | 基本只读 |
| `09-per-book-self-optimization.md` | 自优化系统设计定稿（自省/信任度/注入） | 设计变更时 |
| `10-frontend-api-contract.md` | 前后端对接契约（端点 + SSE 事件 + 数据表） | 接口变更时 |
| `11-plotline-ledger.md` | 伏笔账本设计定稿 | 设计变更时 |

## 归档（`../archive/claude-guide-legacy/`）

已完成阶段的历史文档，仅作回溯参考，**新工作不依赖**：

- `02-architecture.md` —— arch-refactor 目标架构规划（已实现，现状见 00）
- `03-roadmap.md` —— M0–M5 路线图（已全部完成）
- `05-progress-tracker.md` —— 重构期进度日志（活跃进度由 trellis 任务承担）
- `07-reference-takeaways.md` —— 参考项目第一轮提炼（已被 08 吸收）
- `m5-memory-research.md` —— M5 记忆系统研究笔记（结论已入 07/08）

更早的 `../archive/codex-guide/` 是 Codex 时期文档，仅作历史参考。

## 文档纪律

- **设计定稿**（需求讨论 + 评审后）：写入 claude-guide（09/11 模式），实现后更新状态
- **活跃进度**：trellis 任务 + 记忆系统承担，不再维护进度日志文档
- **一次性记录**（dogfood 报告、实验数据）：放 `docs/archive/`，不污染 claude-guide
