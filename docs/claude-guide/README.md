# Claude 开发指导文档集（claude-guide）

本目录是项目新方向的**唯一权威规划文档**，作用等同于上一版的 `codex-guide`（已归档至 `../archive/codex-guide/`）。每次开发 session 开始时，按以下顺序阅读：

1. **`05-progress-tracker.md`** —— 当前进度与下一步（每次必读，每次必更新）
2. **`01-vision.md`** —— 项目重新定义与北极星目标
3. **`03-roadmap.md`** —— 分阶段路线图与每阶段验收标准
4. 其余文档按需查阅

## 文档清单

| 文档 | 内容 | 更新频率 |
| --- | --- | --- |
| `01-vision.md` | 项目重新定义：novelv3 是什么、不是什么、成熟度阶梯 | 方向变化时 |
| `02-architecture.md` | 目标架构：Agent 内核、工具系统、记忆系统、保留/删除清单 | 架构决策时 |
| `03-roadmap.md` | M0–M5 分阶段路线图，每阶段有可验证的退出标准 | 阶段推进时 |
| `04-development-rules.md` | 开发规则：测试纪律、文件预算、验证命令、绞杀式迁移规则 | 规则变化时 |
| `05-progress-tracker.md` | 活跃进度追踪（唯一可频繁改动的文档） | **每次 session** |
| `06-decisions.md` | 新架构决策记录（ADR），含对旧 ADR 的继承/推翻判定 | 决策时 |
| `07-reference-takeaways.md` | 三个参考项目的核心优点提炼与本项目的适配方案 | 基本只读 |

## 与旧文档的关系

- `../archive/codex-guide/` 是上一版（Codex 时期）的指导文档，**仅作历史参考**，与本目录冲突时以本目录为准。
- 上一版的制度记忆（已完成什么、踩过什么坑、为什么做某决策）已经吸收进本目录各文档，正常开发不需要回读归档。
- 例外：`06-decisions.md` 中标注「继承」的旧 ADR，其完整论证仍在 `../archive/codex-guide/06-architecture-decisions.md`。

## 核心原则（一句话版）

> 把 novelv3 从「带 LLM 调用的确定性工作流引擎」翻转为「模型驱动的工具调用 Agent」，
> 保留上一版用真实 dogfood 换来的护栏（循环风险检测、审批门、溯源、预算），
> 删除模拟 Agent 的脚本化编排层，
> 最终长成一个能稳定写百万字网文的专业 Agent。
