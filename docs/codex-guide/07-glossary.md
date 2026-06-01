# 07 · 术语表

> **最后更新**: 2026-06-01
> **版本**: v1.0
> **用途**: 项目特有术语、缩写和概念的定义，确保理解一致

---

## 一、项目特有术语

### novelv3

本项目的代号。当前迭代目标是将其打造为专精网文写作的长期记忆 Agent。

### Agent（vs 工具）

在 novelv3 的语境中：
- **工具** 是被动调用的功能（如"生成大纲"按钮）
- **Agent** 是能自主感知项目状态、编排工具调用、从反馈中学习的系统

### 网文 / 网络小说

指在网络上连载的长篇小说，通常特征：
- 百万字级别（100 万字 = 约 1000 章，每章 1000-3000 字）
- 连载周期长（数月到数年）
- 需要严格的世界观一致性和角色连续性

---

## 二、核心模块名

### Hermes

novelv3 的**创作流程控制模块**。命名来自希腊神话中的信使之神（负责传递信息和维持秩序）。

核心职责：
- 诊断项目当前状态（缺什么、该做什么）
- 管理 pending action（待用户确认的操作）
- 提供前端刷新指令（ui_hint、refresh_targets）
- 管理对话 session 和历史

### Athena

novelv3 的**世界模型模块**。命名来自希腊神话中的智慧女神（负责知识和策略）。

核心职责：
- 管理结构化世界实体（角色、地点、事件等）
- 维护世界事实的版本和一致性
- 提案审批流程（WorldProposalBundle）
- 多层次一致性检查（layered checker）

### Memory Tree

借鉴 openhuman 的分层记忆结构。将小说内容组织为树形结构（卷→章→节→段落），每个节点有摘要，Agent 可以按需展开。

### World Model / 世界模型

Athena 管理的结构化世界观数据，包括：角色、地点、势力、物品、规则、关系、时间锚点、事件、事实声明等实体，以及它们之间的关系。

---

## 三、架构概念

### Descriptor / Adapter / Execution（工具三层）

Agent 工具的三种组件：
- **Descriptor（描述符）**：定义工具的元数据（名称、参数、权限、是否需要审批）
- **Adapter（适配器）**：转换工具调用的输入格式
- **Execution（执行器）**：执行实际的业务逻辑

### IntentRouter / 意图路由

将用户的自然语言消息映射为具体的操作意图（如"写第 10 章"→ `generate_chapter` 意图）。

### Pending Action / 待处理动作

Hermes 在诊断项目状态后生成的、需要用户确认的操作建议。用户可以选择执行、修改或忽略。

### Followup / 后续建议

Agent 在完成一个操作后自动生成的下一步建议。与 Pending Action 不同，Followup 是在操作完成后生成，Pending Action 是在状态诊断后生成。

### Proposal Bundle / 提案包

Athena 中一次世界模型变更的包装：
- `WorldProposalBundle`：变更包的容器
- `WorldProposalItem`：具体的候选事实
- `WorldProposalReview`：用户的审阅记录

### Profile Version / 档案版本

世界模型版本管理的机制。每个项目有一个当前 profile version，所有世界数据绑定到特定版本，防止版本混用。

### Request Lane / 请求通道

前端异步请求的隔离机制。每个请求带 requestId 和 project scope version，迟到的不匹配请求被丢弃。

### Context Block / 上下文块

Trace 系统中记录的 AI 调用上下文组成部分。包括 prompt 模板、检索证据、世界模型节点、章节上下文、用户反馈等。

---

## 四、开发与测试术语

### Dogfood / 狗粮

"Eating your own dog food"的缩写，指开发者自己使用自己的产品。在 novelv3 中指用真实的小说生成来测试系统。

### Longform Smoke / 长篇烟雾测试

`scripts/longform_scale_smoke.py` 的合成测试，模拟千章/百万字项目来验证系统的规模稳定性。

### UAT / 用户验收测试

手工进行的真实场景测试。在 novelv3 中通常指一次完整的"设定→大纲→写多章→审稿→修订"流程。

### Codex

AI 编程 agent 的代称。在本文档中指自动化开发 novelv3 的 AI agent。

---

## 五、参考项目名

### openclaw

TypeScript 实现的多通道 AI 网关和消息平台。novelv3 主要借鉴其 Agent 网关架构、工具循环检测和子 Agent 管理。

### hermes-agent

Python 实现的自改进 CLI Agent（Nous Research 出品）。novelv3 主要借鉴其运行循环、上下文压缩和迭代预算管理。

### openhuman

Rust 核心 + React/TypeScript 前端的桌面 AI 助手（Tauri 应用）。novelv3 主要借鉴其 Memory Tree 分层记忆、StopHooks 策略层和 AgentDefinition 配置化。

---

## 六、技术缩写

| 缩写 | 全称 | 含义 |
|------|------|------|
| API | Application Programming Interface | 前后端通过 REST API 通信 |
| FTS / FTS5 | Full-Text Search | SQLite 全文搜索能力 |
| KV-cache | Key-Value Cache | LLM 推理中的注意力缓存，上下文压缩会破坏它 |
| LLM | Large Language Model | 大语言模型（GPT-4、Claude 等） |
| ORM | Object-Relational Mapping | 对象关系映射（本项目使用 SQLAlchemy） |
| RAG | Retrieval-Augmented Generation | 检索增强生成——先检索相关信息再生成 |
| SQL | Structured Query Language | 结构化查询语言 |
| TDD | Test-Driven Development | 测试驱动开发 |
| UX | User Experience | 用户体验 |
| UAT | User Acceptance Testing | 用户验收测试 |

---

## 七、网文创作术语

| 术语 | 含义 |
|------|------|
| 设定 / Setup | 小说的世界观基础设定（时代、地理、力量体系、社会结构等） |
| 大纲 / Outline | 章节级别的情节规划 |
| 故事线 / Storyline | 贯穿多章节的情节主线（主线、支线、伏笔） |
| 卷 / Volume | 小说的宏观组织结构，多章组成一卷 |
| 爽点 | 网文中读者期待的满足感和情绪高潮段落 |
| 伏笔 / Foreshadowing | 前期埋设、后期呼应的线索 |
| 断章 / Cliffhanger | 章节末尾的悬念钩子 |
| 人设 / Character Setting | 角色的性格、外貌、能力、背景故事设定 |
| 打脸 / Face-slapping | 网文中常见的反转/打脸情节模式 |
| 金手指 / Golden Finger | 主角的特殊能力或优势 |
| 世界观 / Worldbuilding | 小说虚构世界的规则、历史、文化和逻辑体系 |
