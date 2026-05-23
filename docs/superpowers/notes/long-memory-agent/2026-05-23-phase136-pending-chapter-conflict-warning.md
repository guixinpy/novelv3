# Phase136 Report: Pending Chapter Conflict Warning

## 阶段目标

把 Phase135 的 `chapter_target_conflict` 从后端描述文本提升为前端 pending action card 内的独立警示，避免用户在确认前漏看重复章节生成风险。

## 实际完成

- `frontend/src/components/chat/ActionCard.vue`
  - 新增 `chapterTargetConflict` 计算属性，读取 `action.params.chapter_target_conflict`。
  - 新增 `actionCopy` 计算属性，在独立 warning 存在时移除后端描述中的重复“注意”句。
  - 新增 `data-testid="chapter-target-conflict"` warning 区块。
  - warning 文案明确提示：目标章节已有待确认或运行中的生成任务，确认前检查是否仍要覆盖同一章节。
- `frontend/src/components/chat/ChatMessage.test.ts`
  - 新增组件测试，覆盖 warning 渲染和普通描述去重。

## 设计约束

- 不改变后端参数契约和确认行为。
- 不新增新的全局组件或状态管理。
- 警示区块内嵌在现有 ActionCard 中，避免扩大 UI 结构变更。

## 小说进度

本阶段没有生成新章节。原因：本阶段修复的是长篇自动续写中的确认前风险提示，属于 Agent 控制面 UX。

## 已修复的问题

- 显式章节冲突只能通过后端拼接到长描述里的“注意”句看到，确认按钮附近缺少独立警示。
- 描述文本和警示文本会潜在重复，现在前端在渲染 warning 时会剥离普通描述中的重复注意句。

## 未修复但记录的问题

- warning 目前只覆盖 pending action card；历史消息和任务列表尚未展示冲突风险。
- 没有做浏览器端截图验证；本阶段使用组件测试和 build 作为 T1 验证。
- 后续可把冲突提示扩展为操作分支：查看占用任务、取消旧任务、继续覆盖。

## 验证证据

- RED:
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts -t "renders pending chapter conflict as a warning before confirmation"`
  - 结果：`1 failed`
  - 失败原因：找不到 `[data-testid="chapter-target-conflict"]`，ActionCard 只渲染普通描述。
- GREEN:
  - 同一 targeted 命令。
  - `1 passed`
- Component regression:
  - `npm run test:unit -- src/components/chat/ChatMessage.test.ts`
  - `11 passed`
- Frontend build:
  - `npm run build`
  - `vue-tsc --noEmit && vite build` 成功，Vite 输出 `✓ built in 5.67s`。
- Hygiene:
  - `git diff --check`
  - 退出码 0，无输出。
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - 退出码 1，无匹配。

## 下一阶段建议

Phase137 建议把 `generate_chapter_range` 纳入 reserved target 计算，避免批量生成任务与单章续写互相撞车。
