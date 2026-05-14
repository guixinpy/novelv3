# Phase 136: Workspace 冷启动对话消息体积控制

## 背景

`workspace-bootstrap` 会在进入项目时返回 Hermes 与 Athena 最近对话。
旧实现直接返回最近 80 条完整消息内容。长篇项目中，用户可能粘贴长设定、长反馈、长章节片段，导致冷启动响应被少数大消息拖大。

常规 `/dialog/messages` 接口仍需要保留完整历史读取能力，本阶段只收敛冷启动体积。

## 修复

- `DialogMessageService.list_messages` 增加可选 `max_content_chars`。
- `workspace-bootstrap` 调用对话列表时启用 6000 字符预览上限。
- 被截断的消息会返回：
  - `content_truncated: true`
  - `original_content_length`
- 常规消息接口不传该参数，保持原行为。
- 前端 `ChatHistoryMessage` 类型补充可选截断字段。

## 验证

- 先新增失败测试：
  - `backend/tests/test_workspace_bootstrap.py::test_workspace_bootstrap_truncates_large_dialog_messages`
  - RED：旧实现返回完整长消息，且没有截断标记。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py::test_workspace_bootstrap_truncates_large_dialog_messages -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialog_messages_pagination.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_athena_dialog.py -q`
  - `npm run test:unit -- src/stores/project.workspace.test.ts src/stores/chat.workspace.test.ts`

## 后续观察

- UI 后续可对 `content_truncated` 显示“此为冷启动预览，打开消息详情查看完整内容”。
- 如果常规历史接口也出现大响应问题，应增加显式 `preview=true` 或独立详情接口，而不是默认破坏完整聊天历史。
