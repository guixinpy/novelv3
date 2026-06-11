# Codex 开发指导文档 · 入口

> **最后更新**: 2026-06-06
> **版本**: v1.0
> **状态**: 活跃维护

---

## 这份文档是什么

本目录 (`docs/codex-guide/`) 是 novelv3 项目的 **codex 开发指导文档集**。它的目标读者是 AI codex agent（以及接手项目的人类开发者）。

**核心作用**：当 codex 的上下文窗口被压缩、丢失了之前的讨论和决策时，这套文档能让下一轮 codex 快速恢复对项目目标、架构、进度和规则的认知，不重复踩坑、不偏离方向。

**本文档不涉及具体代码**，只描述方向、规则、状态和决策。具体代码实现请直接阅读源码。

**使用边界**：本系列文档主要用于规范和记录 codex 的工作过程，帮助上下文恢复；其中的方向和优先级不是绝对正确的路线图。codex 可以根据实际代码状态、真实 dogfood 反馈，以及 openclaw / hermes-agent / openhuman 的优秀模式自行吸收、取舍和调整，但必须把新的判断、进度和决策同步更新到本文档集。

---

## 项目一句话目标

> 将 novelv3 打造为**专精网文写作的长期记忆 Agent**：以对话驱动、具备自主工具编排能力、支撑百万字/千章级网络小说创作。

---

## 文档索引

| 序号 | 文档 | 用途 | 何时读 |
|------|------|------|--------|
| 01 | [愿景与架构目标](./01-vision.md) | 项目的最终目标形态、核心设计理念 | 首次了解项目、方向偏离时重读 |
| 02 | [模块清单与状态](./02-module-inventory.md) | 每个核心模块的当前状态、目标状态、关键文件 | 需要了解某个模块的现状时 |
| 03 | [参考项目模式映射](./03-reference-patterns.md) | 从 openclaw/hermes-agent/openhuman 学到的模式 | 设计新能力时需要参考外部模式 |
| 04 | [开发规则与约束](./04-development-rules.md) | codex 必须遵守的工程规范和质量门禁 | 每次动手前、不确定做法时 |
| 05 | [进度追踪](./05-progress-tracker.md) | 各开发轨道的当前进度、下一步任务 | **每次 session 必读**，了解最新进度 |
| 06 | [架构决策记录](./06-architecture-decisions.md) | 关键设计决策及其理由 | 质疑现有设计时、做类似决策时 |
| 07 | [术语表](./07-glossary.md) | 项目特有术语和概念定义 | 遇到不熟悉的术语时 |
| 08 | [实施架构框架](./08-implementation-architecture.md) | 能力切片、Thin Shell、文件预算和验证闭环 | 开始长期代码推进、触碰巨型文件或新增 Agent 能力前 |

---

## 快速查找指南

### 我是新来的 codex，第一次接手这个项目

1. 先读 [01-愿景与架构目标](./01-vision.md) 理解我们要做什么
2. 再读 [04-开发规则与约束](./04-development-rules.md) 知道怎么做事
3. 然后读 [05-进度追踪](./05-progress-tracker.md) 知道当前做到哪了
4. 需要了解具体模块时查 [02-模块清单与状态](./02-module-inventory.md)
5. 遇到不认识的术语查 [07-术语表](./07-glossary.md)

### 我要开始写代码了

1. 先看 [04-开发规则与约束](./04-development-rules.md) 里的"编码前检查清单"
2. 再看 [08-实施架构框架](./08-implementation-architecture.md) 确认能力切片、文件预算和验证闭环
3. 再看 [05-进度追踪](./05-progress-tracker.md) 确认当前任务没有被别人在做
4. 完成后更新 [05-进度追踪](./05-progress-tracker.md)

### 我做出了影响架构的决策

1. 在 [06-架构决策记录](./06-architecture-decisions.md) 中追加记录
2. 如果影响了模块状态，更新 [02-模块清单与状态](./02-module-inventory.md)
3. 如果影响了进度，更新 [05-进度追踪](./05-progress-tracker.md)

### 上下文被压缩了，我要快速恢复认知

按优先级读：
1. **本文档**（你已经在读了）— 快速了解文档结构
2. **[05-进度追踪](./05-progress-tracker.md)** — 最重要，知道现在做到哪了
3. **[08-实施架构框架](./08-implementation-architecture.md)** — 恢复能力切片、文件预算和执行框架
4. **[01-愿景与架构目标](./01-vision.md)** — 恢复方向感
5. **[04-开发规则与约束](./04-development-rules.md)** — 恢复做事方法

---

## 项目地图（30 秒概览）

```
novelv3/
├── backend/app/
│   ├── api/              # FastAPI 路由层
│   ├── core/             # 核心逻辑（意图路由、检索、trace 等）
│   ├── models/           # SQLAlchemy 数据模型
│   ├── schemas/          # Pydantic API schema
│   ├── services/
│   │   ├── actions/      # Hermes 动作系统（proposal/execution/result）
│   │   ├── dialog/       # 对话管理（session/messages）
│   │   ├── tasks/        # 后台任务队列
│   │   ├── workspace/    # 工作空间服务
│   │   ├── writing/      # 写作相关服务
│   │   └── writing_agent/  # ★ Agent 核心——最重要目录
│   └── prompting/        # Prompt 模板和 provider
├── frontend/src/
│   ├── views/            # 页面视图
│   ├── components/       # UI 组件（含 modelTrace/等）
│   ├── stores/           # Pinia 状态管理
│   ├── api/              # 前端 API 调用
│   └── router/           # 前端路由
├── docs/
│   ├── codex-guide/      # ★ 本目录——开发指导文档
│   ├── archive/others/    # 参考项目模式提取报告等历史材料
│   ├── archive/          # 历史归档
│   └── superpowers/      # 当前活跃的设计/计划
├── references/agent-projects/  # 本地参考源码快照
└── scripts/              # 工具脚本（含 longform smoke）
```

---

## 核心原则（不可妥协）

1. **Agent-first**：novelv3 的目标是成为能自主创作网文的 Agent，不是"带 AI 辅助的写作工具"
2. **对话驱动**：一切操作通过对话入口，Agent 自主编排工具调用
3. **长期记忆**：世界观、角色、情节的记忆不能依赖上下文窗口
4. **可审计**：所有 AI 调用必须可追溯（model call trace）
5. **可恢复**：任何操作出错后必须可回滚
6. **真实验证**：用真实小说生成来压力测试，不以"架构更完整"作为完成标准
7. **模块边界可调整**：不死守旧形式，允许必要的扩展、重构和精简

---

## 三个参考项目

| 项目 | 语言 | 核心价值 |
|------|------|---------|
| **openclaw** | TypeScript | 多通道 Agent 网关、5 级循环检测、子 Agent 管理 |
| **hermes-agent** | Python | Agent 运行循环、上下文压缩、迭代预算 refund 机制 |
| **openhuman** | Rust+TS | Memory Tree 分层记忆、StopHooks 策略层、AgentDefinition |

源码快照位于 `references/agent-projects/`，原始模式分析报告已归档到 `docs/archive/others/01-reference-patterns-report.md`。

---

## 维护规则

- 本文档集在每次重大开发 session 后必须更新
- 最频繁更新的文档是 [05-进度追踪](./05-progress-tracker.md)
- 每个文档底部有"最后更新"时间戳
- 如果发现文档内容与实际情况不符，**立即修正**
- 不要让文档变成"考古现场"——过期的内容要么删除，要么移到 archive
