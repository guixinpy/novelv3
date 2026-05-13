# Athena World Model Hardening Design

## Goal

把 Athena / world-model 从“功能可用”推进到“长期本地使用稳定”：统一上下文拼装、让检索索引随世界事实变化增量更新、收敛提案事务边界，并降低 Athena 前端入口的状态耦合。

## Scope

本阶段一次性覆盖之前识别出的明显优化项，但仍然保持本地项目边界：

- 不引入 Redis、队列、外部向量库或后台 worker。
- 不重写 `world_projection.py` 的核心投影算法。
- 不改变既有公开 API 路径，除新增 Setup 导入预览接口外保持兼容。
- 每阶段必须有可运行链路测试，正常后再进入下一阶段。

## Architecture

### 1. World Context Assembler

新增 `backend/app/core/world_context_assembler.py`，作为 Athena/Hermes/章节上下文的统一拼装入口。它负责查询当前 profile、Setup 兜底、实体、关系、规则、事实、事件，并输出结构化 `context_blocks`、章节写作 `sections`、以及 prompt 文本。

`context_injection.py` 和 `athena_longform.py` 只保留对外函数，内部委托 assembler，避免两套上下文选择逻辑继续漂移。

### 2. Local Incremental Retrieval Index

`athena_retrieval.py` 增加本地增量同步能力：

- `sync_fact_retrieval_document()`：审批确认事实后写入/更新对应 `world_fact` 文档。
- `delete_fact_retrieval_document()`：回滚事实后删除对应索引文档。
- `search_retrieval()` 先取有限候选集，再在 Python 内评分，避免长篇后全表向量遍历。

写路径仍然同步执行，适合本地 SQLite；核心审批事务成功后再同步检索，避免检索失败破坏事实持久化。

### 3. Proposal Workflow Boundary

`world_proposal_service.py` 不改变外部 API，但拆出小的状态/复制工具：

- 审批状态判断集中在 `world_proposal_state.py`。
- candidate/item/claim 字段复制集中在 `world_proposal_records.py`。
- 审批和回滚后触发投影 cache 失效与检索索引同步。

目标不是做大框架，而是把 800+ 行文件中最容易重复出错的字段拷贝和状态规则收敛。

### 4. Setup Import Preview

新增只读 preview：

- 后端返回即将导入的 characters/locations/factions/artifacts/rules 计数与候选名称。
- 前端 Overview 在未导入 world-model 时显示导入预览摘要。
- 真正导入仍使用现有 `import_setup_to_world_model()`，不增加复杂确认流。

### 5. Athena Frontend Shell Split

前端保留既有 UI，但拆边界：

- `AthenaSubnav.vue` 只负责 section 导航和动作按钮。
- `useAthenaSectionLoader.ts` 只负责 section 加载策略。
- `worldModel` store 增加 lane loading/error，避免 dashboard/projection/proposal 共用一个 loading/error。

## Testing

每阶段必须验证：

- 后端 targeted pytest：context、retrieval、proposal、frontend API。
- 前端 targeted Vitest：store、Athena view/subnav/overview。
- E2E：Overview -> import preview -> proposals -> review -> retrieval/projection。
- 最终 `RUN_E2E=1 scripts/verify_local_quality.sh`。

## Risks

- 上下文统一时最容易破坏 prompt 文本顺序。测试必须断言关键 block 和文本片段。
- 增量索引如果和审批事务混在一起，可能让检索失败影响审批。实现上检索同步只在核心事务成功后执行。
- 前端拆分不能变成设计重做。只拆 shell 和 loader，不调整视觉风格。
