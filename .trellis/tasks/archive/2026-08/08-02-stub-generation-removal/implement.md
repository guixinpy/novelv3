# P1 stub 生成端点体系清理 · 执行计划

> 删除类任务：每步先 grep 引用归零再删；保留 WritingAgentRun 表与 generate_chapter 真路径。

## 阶段 1：后端 stub 符号清理

### 1.1 dialog_utils.py
- [ ] 删 `execute_agent_api_tool`、`AgentApiToolRunResult`、`_raise_if_agent_generation_failed` 及仅 stub 使用的符号
- [ ] grep 确认其余模块不再引用（chapters/athena_*/action 后续步骤删完后再复检）

### 1.2 chapters.py
- [ ] 删 generate 端点 + `_raise_if_agent_chapter_generation_failed` + `CHAPTER_GENERATION_ERROR_STATUS_CODES` + `CHAPTER_GENERATE_ENTRYPOINT`（若仅端点用）
- [ ] 保留 create_or_replace_chapter（真生成，修订/action 用）

### 1.3 athena_ontology.py / athena_evolution.py
- [ ] 删 generate_ontology / generate_evolution_plan / _execute_evolution_generate_tool + ATHENA_* 常量 + `_with_agent_metadata`/`_raise_if_agent_generation_failed` 等假错误管道
- [ ] 保留 GET 查询端点（get_evolution_plan 等）

### 1.4 action_execution_service.py
- [ ] 删 3 个 stub 动作分支 + label_map 清理；generate_chapter 保留
- [ ] 验证门：`python -m pytest tests/ -q` 全绿（预期部分测试删除/改造后）

## 阶段 2：测试清理

- [ ] test_action_execution.py：删 3 个 stub 动作用例（保留 generate_chapter/缺项目）
- [ ] athena_ontology/evolution 测试中 generate 端点用例删除
- [ ] 验证门：`grep -rn "execute_agent_api_tool\|generate_ontology\|generate_evolution_plan" backend/app backend/tests` 归零

## 阶段 3：前端清理

- [ ] client.ts：删 3 个生成方法（或注释引导 v2 会话）
- [ ] stores/project.ts：删 3 个函数（参照 generateChapter 先例）
- [ ] 验证门：`grep -rn "generateSetup\|generateStoryline\|generateOutline" frontend/src` 归零
- [ ] 前端 vitest + vue-tsc 通过

## 阶段 4：收尾

- [ ] 后端全量 pytest + 前端 vitest + vue-tsc 全绿
- [ ] progress-tracker 记录；独立 commit（`refactor: stub-removal`）
- [ ] 归档任务

## 回滚点

- 阶段 1 完成即安全点（后端 stub 全删、测试绿）
- 阶段 3 前端删除前确认组件零调用（已核实）
