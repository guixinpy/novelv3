# Athena World Model P1/P2 Optimization Design

## Goal

把 Athena / world-model 剩余明显短板一次性收口到“本地长期可用”的工程状态：检索能召回深处证据，章节与 Setup 抽取不再只靠极浅规则，检索失败可诊断，审批不被索引副作用卡死，前后端模块边界更清楚，UI 面向创作者而不是调试者。

## Scope

- 不引入 Redis、消息队列、外部向量库、后台 worker。
- 不改变既有公开 API 路径；拆路由时通过 router include 保持兼容。
- 不重写投影核心算法，只补召回、抽取、诊断和模块边界。
- 每阶段必须有对应链路测试，正常后再进入下一阶段。

## Architecture

### 1. Retrieval Recall And Diagnostics

`search_retrieval()` 不能先按 source/chapter/chunk 取前几百条再评分。改成本地 SQLite 友好的两段候选：

- 用查询 token 生成 lexical shortlist，优先召回文本命中的 chunk。
- 再补稳定 fallback 候选，保持无 token 命中时仍可返回结果。
- Python 内统一去重评分，避免长篇后部相关内容被候选上限截断。

`WorldContextAssembler` 不再吞掉检索异常。生成链路不中断，但上下文会带结构化 warning，方便 UI/日志/测试定位。

### 2. Better Local Extraction

章节分析不再只抽人物名：

- 基于已知世界实体做地点/组织/物件共现识别。
- 为章节生成轻量事件候选。
- 生成人物-地点共现场景候选，作为后续人工审批素材。

Setup 导入候选不再只依赖引号：

- 继续保留引号高置信提取。
- 增加中文专名/短语窗口提取，按字段上下文分类。
- preview 与 import 使用同一套候选函数，避免“预览有、导入无”或反过来。

### 3. Approval Side Effect Boundary

审批事实的主事务先完成。检索索引同步改成 post-commit best-effort：

- 同步成功则立即可检索。
- 同步失败不回滚已审批事实。
- 失败写入日志并允许后续重建/再次触发，不在本地项目里引入队列。

### 4. Backend API Boundary

`backend/app/api/athena.py` 拆成小 router 模块，保持 URL 兼容：

- ontology/setup import
- retrieval
- dialog/optimization
- projection/proposals

目标是减少单文件认知负担，不做路由体系重写。

### 5. Frontend Store And Creator UI

保留 `useAthenaStore()` 作为兼容 facade，但把 retrieval/proposals/chat/optimization 逻辑拆到 focused modules 或 focused stores。

UI 优先服务创作者：

- RetrievalPanel 展示“证据出处、章节位置、命中原因、可用动作”，弱化技术分数。
- ProjectionViewer 按人物、地点、规则、事实分组，显示冲突/待确认提示。
- 仍保留必要调试信息，但不作为主视觉。

## Testing

- Stage 0：worktree baseline。
- Stage 1：retrieval recall + context warning targeted pytest。
- Stage 2：chapter/setup extraction targeted pytest。
- Stage 3：proposal review post-commit sync targeted pytest。
- Stage 4：API split route compatibility targeted pytest。
- Stage 5：frontend store/UI Vitest + build。
- Stage 6：Athena E2E + `scripts/verify_local_quality.sh`。

## Risks

- 检索召回扩大后可能变慢。候选上限必须保守，且只使用 SQLite `LIKE` + Python scoring。
- 抽取规则太激进会制造噪音。所有新候选必须走 proposal 审批，不直接写 confirmed fact。
- 拆 API/store 容易破坏导入路径。必须靠路径兼容测试和现有 Vitest 锁住。
