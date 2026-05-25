# Phase124 Report: Approval Decision View

## 阶段目标

把 Phase123 写入 `action_result.data.approval_decision` 的审批决策元数据，投影为对话里可见的中文审计摘要。

## 实际完成

- `backend/app/services/actions/action_result_view.py`
  - `action_result_view(...)` 现在会在存在 `approval_decision` 时返回 `detail_items`。
  - `confirm/cancel/revise` 已本地化为 `已确认/已取消/要求修改`。
  - 原始 `approval_contract_hash` 不进入 `action_result_view`，只显示 `审批契约: 已绑定`。
- `frontend/src/components/chat/ChatMessage.vue`
  - 支持渲染 `action_result_view.detail_items`。
  - 审计行显示在操作结果下方，保持紧凑，不从原始 `action_result.data` 自行拼接内部字段。
- `frontend/src/api/types.ts`
  - `ActionResultView` 增加可选 `detail_items` 类型。
- `backend/tests/test_dialogs.py`
  - 扩展审批决策测试，覆盖后端视图投影和 hash 隐藏。
  - 更新旧的 action_result_view 精确对象断言，接受新的审计详情行。
- `frontend/src/components/chat/ChatMessage.test.ts`
  - 新增 UI 测试，验证审计详情渲染且不泄露 `approval:` 原始 hash。

## 小说进度

本阶段没有生成新章节。原因：本阶段仍是 Agent 工具审批链路的可观察性建设，为后续真实长篇生成提供可审计基础。

## 发现的问题

- 根目录没有 `package.json`，前端测试必须在 `frontend/` 目录运行。本次第一次 RED 命令在根目录触发 `ENOENT`，随后在 `frontend/` 正确重跑并得到预期失败。
- Browser 插件导航/快照工具未暴露到当前工具集；本阶段用组件测试和生产 build 覆盖 UI 改动，未做真实页面浏览器验收。

## 已修复的问题

- 审批决策元数据不再只存在于后端原始 `action_result.data`，现在会被投影成用户可读的中文审计摘要。
- 对话 UI 可以展示审批决策的关键信息，同时避免暴露内部审批 hash。

## 未修复但记录的问题

- 审批决策尚未进入独立 Trace/Event 页面。
- 世界模型写入审批路径尚未统一接入该审计投影。
- 后续需要恢复可用的浏览器自动化工具链，便于每次 UI 改动后做真实页面 smoke。

## 验证证据

- Backend RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
  - 失败原因：`KeyError: 'detail_items'`。
- Frontend RED:
  - `npm run test:unit -- ChatMessage.test.ts`，在 `frontend/` 目录运行。
  - 失败原因：组件文本未包含 `用户决策`。
- Targeted GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
  - `1 passed in 0.18s`
  - `npm run test:unit -- ChatMessage.test.ts`
  - `10 passed`
- Backend dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - `65 passed in 23.61s`
- Frontend build:
  - `npm run build`，在 `frontend/` 目录运行。
  - `vue-tsc --noEmit && vite build` 通过。
- Hygiene:
  - `git diff --check`
  - 退出码 0。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 无匹配。

## 下一阶段建议

Phase125 建议推进 Trace/Event 化：把审批决策、工具调用、写入结果串成同一个可查询事件链，为后续“Agent 自主编排多个模块”提供统一审计基座。
