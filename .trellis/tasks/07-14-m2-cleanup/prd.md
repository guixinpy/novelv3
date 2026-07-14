# PRD · M2 清理收尾：删除旧编排层

## 背景

评估发现 `services/writing_agent/` 目录 58 文件 / 21,702 LOC 仍在代码库中，被 v1 端点引用。这直接违背 vision 文档核心禁令：**"禁止再出现「意图分类 → 查表选 plan → 按脚本逐步执行」的模式"**。

M2 路线图中的退出标准明确要求：`git grep intent_router|run_service|tool_descriptors` 零命中、后端 LOC 下降 ≥30%。

## 目标

删除 `services/writing_agent/` 整个目录，切断所有外部引用链，使代码库中 `intent_router`/`run_service`/`tool_descriptors` 三个符号零命中。

## 范围

### 删除目标

- `backend/app/services/writing_agent/` — 整个目录（58 files, 21,702 LOC）
- `backend/app/api/dialogs.py` — v1 对话端点
- 任何仅为旧编排层服务的测试文件

### 保留/不改

- `backend/app/agent/` — 新内核（全部文件）
- `backend/app/tools/` — 工具定义（全部文件）
- `backend/app/api/chapters.py` — v1 端点，需评估迁移或保留

## 验收标准

- [ ] `git grep -E "intent_router|run_service|tool_descriptor" backend/app/ -- '*.py'` 零命中
- [ ] `backend/app/services/writing_agent/` 目录不存在
- [ ] `backend/app/api/dialogs.py` 文件不存在
- [ ] `pytest tests/ -q` 全绿（730+ passed）
- [ ] 前端 `npm test` 全绿（576 tests）
- [ ] 前端 `npm run build` 无错误
- [ ] 新 agent 内核功能正常（对话 + 工具调用未受影响）
