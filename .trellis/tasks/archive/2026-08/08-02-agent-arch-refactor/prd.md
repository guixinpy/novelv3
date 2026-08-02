# agent 架构重构：以 agent 为核心重新设计后端

## Goal

本项目经历多轮重构，现有后端架构存在历史遗留缺陷（模块级全局状态、字符串耦合、粗糙 token 估算等），且业务模块与 agent 内核的边界是历次演进中逐步形成的，不是一次顶层设计的结果。目标：**从基础重新设计后端架构，使 agent 成为架构核心**——吸收 docs/references/agent-projects/ 下三个参考项目（hermes-agent / openclaw / openhuman）的优秀设计，同时保留现有架构经实战验证的优点（领域无关内核、无状态引擎、事件驱动、provider 抽象、多层容错）。

## Background

### 现有架构盘点（backend/app）

| 模块 | 文件 | 行数 | 定位 |
|---|---|---|---|
| core/ | 78 | 17,352 | 核心逻辑，历次演进主战场（含 world_* 6k 行、revision 2k 行） |
| api/ | 29 | 5,834 | 路由层（v1/v2 混合） |
| models/ | 38 | 2,274 | SQLAlchemy 模型 |
| services/ | 19 | 2,121 | 五个子域服务（actions/dialog/tasks/workspace/writing） |
| tools/ | 7 | 1,836 | agent 工具（20 个） |
| agent/ | 12 | 1,587 | harness 本体 |
| schemas/ | 20 | 1,601 | Pydantic 契约 |

依赖图：agent/ 零依赖（✓ 保持）；tools → core/agent/models；core → models(40)/schemas/db（业务与 ORM 耦合待解）；api → 全部（组装层）。

### 现有缺陷（重构目标）

1. 【架构级】compaction.py 模块级全局状态，多会话并发互相污染
2. 【架构级】token 估算 `len//2` 粗糙，压缩阈值判定不可靠
3. 【工程质量】guards L4 字符串耦合 registry 错误文案
4. 【工程质量】工具 schema 手写 JSON，与实现无类型绑定
5. 【结构性】core/ 78 文件 1.7 万行无清晰分层
6. 【结构性】循环逻辑可测性弱（590 测试但循环测试少）

### 参考项目研究结论（三份报告已落盘 research/）

- **hermes-agent**（Python，最接近技术栈）：TurnRetryState 对象化、CJK 估算+指纹缓存、压缩失败冷却/无效计数、状态重注入、api_content sidecar、结果归一化、check_fn 能力探测、固定返回结构、声明式 schema、observer 只读契约
- **openclaw**（TS）：steer/followUp 双队列、归一化事件协议+错误编码进流、工具六阶段管线、CJK 加权、compaction 护栏全套、树形 transcript、network 污染标记、goal 轻量目标、子代理 push 模型
- **openhuman**（Rust）：护栏家族（wall-clock/优雅暂停）、plan→execute⇄review→finalize 图、工具结果三级治理、scripted mock 测试、fail-closed 工具可见性、append-only 转录、事件 journal、provider-string+tier、失败分类学

## Requirements

- R1：后端分层重构为 `core/`（agent 内核，领域无关）→ `domain/`（小说业务：writing/memory/retrieval）→ `api/`（新组装层）三层结构
- R2：agent 内核吸收三份研究报告中映射表（design.md §6）的全部 20 项吸收点
- R3：修复现有缺陷 1-4（compaction 全局状态实例化、CJK 估算、L4 错误码化、pydantic schema 生成）
- R4：新 API 完全自由设计（会话中心 + SSE 事件流 + steer/followup/approve/events 重放/workflow 状态）
- R5：保留现有数据兼容（projects/setups/outlines/chapter_contents/longform_memories/entity_candidates 表结构不动）
- R6：归档 world_* 与 revision/optimization 到 docs/archive/arch-refactor/
- R7：mock provider 测试设施（scripted 响应序列 + 请求形状断言），循环行为（重试/护栏/压缩/双队列）确定性测试
- R8：旧后端保持可运行直至阶段 4（新旧并行，新 API 独立前缀）
- R9：阶段 2 末做 1 次真实生成验证（1-2 章）；阶段 5 跑 ≥50 章长程 dogfood 对比指标

## Acceptance Criteria

- [ ] A1：后端分层为 core/domain/api，`core/` 零依赖 domain（grep 验证 + 测试断言）
- [ ] A2：20 项吸收点全部落地（design.md §6 映射表逐项可指认代码）
- [ ] A3：现有缺陷 1-4 修复（compaction 状态实例化验证多会话隔离；CJK 估算单测；L4 按错误码触发；工具 schema 由 pydantic 生成）
- [ ] A4：循环行为测试覆盖 ≥5 条失败路径（重试/护栏/压缩失败/steer 注入顺序/优雅暂停）
- [ ] A5：阶段 2 真实生成 1-2 章成功落库、事件流完整、无护栏误触发
- [ ] A6：200 章历史数据可读，实体转正逻辑等价
- [ ] A7：归档后旧代码无死 import（compileall + grep）
- [ ] A8：阶段 5 dogfood ≥50 章，analyze_dogfood 指标（guard 触发率/压缩质量/错误率/幻觉工具率）不劣于旧基线

## Key Decisions（用户已确认）

| 决策 | 结论 |
|---|---|
| 重构策略 | 设计先行 + 骨架新建（旧后端并行运行至阶段 4） |
| API 契约 | 完全自由（前端后续重写，不对旧契约负责） |
| 测试策略 | 重写为主，纯函数测试（格式/实体/压缩等）随模块移植 |
| 业务范围 | 核心链保留（writing/memory/retrieval ~11k 行迁入）；world_*（6k 行）+ revision/optimization（2k 行）归档；杂项随用随迁 |

## Out of Scope

- 前端重构（后续单独任务）
- 子代理/多 agent 编排（预留扩展点，不进本次）
- goal 轻量目标系统、MCP 接入、OAuth、多 provider 全家桶
- 参考项目本身任何修改

## Technical Notes

- 完整设计见 design.md（架构图/吸收映射表/实施阶段/风险）；执行计划见 implement.md
- 三份研究报告：research/hermes-agent.md、research/openclaw.md、research/openhuman.md
