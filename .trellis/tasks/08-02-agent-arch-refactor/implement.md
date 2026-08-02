# Implement: agent 架构重构执行计划

> 策略：设计先行 + 骨架新建。旧后端保持可运行直至阶段 4，新旧并行（新 API 独立前缀）。
> 测试策略：重写为主，纯函数移植。每次阶段结束有明确验证点。

## 阶段 0：归档准备（现有测试全绿快照）✅ 已完成

> **执行调整（2026-08-02 记录）**：盘点后发现归档对象的真实归属与名字不符——
> - world_* 深度嵌入 12 个核心链文件（athena_longform 36 处引用），提前摘除风险高 → **延迟到阶段 4 随旧后端整体清理**（旧 core 删除时连带归档，无需摘除）
> - revision_feedback / prompt_optimizer / writing_scheduler 检查后确认属核心链（修订反馈格式化/风格规则翻译/写作调度）→ **保留**
> - 实际归档：self_optimization 实验链（learned PromptRule）4 文件 + 引用摘除 6 文件
> - 验证：586 passed（590 - 4 归档测试）

- [x] 0.1 归档 self_optimization 实验链：`core/self_optimization.py` + `api/athena_optimization.py` + `models/prompt_rule.py` + `tests/test_self_optimization.py` → `docs/archive/arch-refactor/`
- [x] 0.2 摘除引用：athena.py（router）/ chapter_revisions.py（2 处调用）/ projects.py（import）/ models/__init__.py（导出）/ 2 个测试文件
- [x] 0.3 残留检查：`grep -r "self_optimization\|PromptRule\|athena_optimization" backend/app backend/tests` 为空
- [x] 0.4 验证：586 passed 全绿

## 阶段 1：内核骨架新建（core/ 全新）

- [ ] 1.1 `core/context/estimate.py`：CJK-aware 估算（ASCII 4字符/token、CJK 1字≈1.5、图片 1500/张）+ 指纹缓存
- [ ] 1.2 `core/turn_state.py`：TurnState 对象（重试计数/压缩标记/错误样本，一次性 guard 收敛）
- [ ] 1.3 `core/loop.py`：无状态回合引擎（迁移现有 run_turn 逻辑 + TurnState + wall-clock + 优雅暂停）
- [ ] 1.4 `core/context/compaction.py`：CompactionState 实例化 + 失败冷却 + 无效压缩计数 + 合理性校验 + 写锁
- [ ] 1.5 `core/context/inject.py`：状态重注入（设定/大纲/人物卡固定 header）+ KV-cache 契约（动态内容骑用户消息）
- [ ] 1.6 `core/tools/`：工具框架（pydantic schema 生成 + 结果归一化 + 失败分类 ClassifiedFailure + artifact 落盘三级治理 + check_fn 能力探测）
- [ ] 1.7 `core/guards/`：五级 guard（L4 改错误码判断）+ 压缩后循环守卫
- [ ] 1.8 `core/events.py`：事件模型 + 稳定 event id + sink 异常隔离 + 凭证打码
- [ ] 1.9 `core/session/`：transcript（append-only + compaction 记录 + 幂等键 + 写锁 + parent_id 预留 + api_content sidecar）
- [ ] 1.10 `core/providers/`：迁移现有 Provider 抽象（stream/complete/重试/Usage）
- [ ] 1.11 `core/harness.py`：有状态外壳（steer/followUp 双队列 + one-at-a-time + 压缩调度 + 快照 callback 注入）
- [ ] 1.12 `core/workflow/`：plan→execute⇄review→finalize 图机制（节点 worker 注入 + 递归上限 + checkpoint + per-step provenance）
- [ ] 1.13 `tests/core/`：mock provider 测试设施（scripted 响应序列 + 请求形状断言）——loop 重试/guard/压缩/steer 注入顺序全部确定性测试

**验证**：`cd backend && python -m pytest tests/core/ -q` 全绿；循环行为（重试/护栏/压缩/双队列）有 ≥1 条失败路径测试

## 阶段 2：最小闭环（新 API + writing 最小链路）

- [ ] 2.1 `domain/writing/` 迁入：generation/（chapter/blocks/render）+ format_checker + structural_similarity + prompt_budget（含现有测试移植）
- [ ] 2.2 `domain/tools/`：write_chapter / check_format / check_structure 注册进新工具框架（pydantic schema + artifact 落盘）
- [ ] 2.3 `api/v2/agent.py`：会话创建 / 消息发送（SSE 事件流）/ steer / followup / approve / events 重放 / workflow 状态
- [ ] 2.4 `api/v2/` 接入 SQLite 既有表（projects/chapter_contents/longform_memories）
- [ ] 2.5 验证：`python -m pytest tests/api_v2/ -q` + **1 次真实生成 1-2 章**（DeepSeek），确认章节落库、事件流完整、无护栏误触发

## 阶段 3：领域迁入（memory → retrieval → entities，逐子域）

- [ ] 3.1 `domain/memory/`：longform_memory + longform_context_summary + project_snapshot + narrative_plan_window + outline_lookup（纯函数测试移植）
- [ ] 3.2 `domain/retrieval/`：athena_retrieval + entity_miner + embedding_service + few_shot + text_mentions + athena_entity_resolver
- [ ] 3.3 工具补齐：plan_arc / track_plotline / get_entities / retrieve 等注册（pydantic schema）
- [ ] 3.4 验证：200 章历史数据可读、实体转正（rule 跨章）逻辑等价；`pytest` 全绿

## 阶段 4：旧代码清理

- [ ] 4.1 删除旧 `core/`（除保留迁移后无引用文件）、旧 `api/`（athena_* 等）、旧 `tools/`、旧 `services/`
- [ ] 4.2 旧测试归档 `docs/archive/arch-refactor/tests-legacy/`
- [ ] 4.3 验证：无死 import（`python -m compileall` + grep 全空）、`pytest` 全绿

## 阶段 5：回归与 dogfood

- [ ] 5.1 新架构全量测试绿 + 覆盖率对比旧基线
- [ ] 5.2 跑一轮长程 dogfood 实验（≥50 章），对比 analyze_dogfood 指标（guard 触发/压缩质量/错误率/幻觉工具）
- [ ] 5.3 更新 docs/claude-guide/05-progress-tracker.md + 归档本任务

## 风险文件与回滚点

| 文件/阶段 | 风险 | 回滚 |
|---|---|---|
| 阶段 1 内核 | 行为与旧循环不一致 | 新旧 loop 并存，mock 测试对比 stop_reason 分布 |
| 阶段 2 API | 真实生成暴露护栏误报 | 调参（阈值/预算），不改结构 |
| 阶段 3 领域迁移 | 行为契约丢失 | 纯函数测试随身移植，逐子域验证 |
| 阶段 4 删除 | 隐藏引用 | 归档而非删除（docs/archive/arch-refactor/），git 可恢复 |

## 提交节奏

每阶段一个 commit（`arch: 阶段 N ...`），阶段 2 真实生成验证后合并到 main 前先给用户演示。
