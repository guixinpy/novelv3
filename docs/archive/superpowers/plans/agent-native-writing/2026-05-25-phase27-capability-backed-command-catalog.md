# Phase27: 能力约束的 Agent 命令目录

## 背景

Phase25/26 已经把旧的模块型斜杠命令收敛为 Agent 控制入口，并把命令目录下沉到后端。但当前 `/api/v1/dialog/chat-commands` 仍主要返回静态注册表，无法说明一个命令背后是否真的有 Agent tool/capability 支撑。

这会让 `/` 命令继续停留在 UI 快捷入口层，而不是 Agent 原生控制面。下一步需要让命令目录受 Agent 工具注册与适配器可用性约束。

## 假设

- `/continue` 和 `/status` 是 Agent 控制命令，应由真实 Agent 工具能力支撑。
- `/clear` 和 `/compact` 是会话控制命令，不要求写作 Agent 工具适配器。
- 旧命令 `/setup`、`/storyline`、`/outline`、`/chapter` 继续作为隐藏兼容别名保留，但不进入公开候选。
- 本阶段只调整目录和前端候选过滤，不改变用户发送命令后的执行语义。

## 成功标准

1. 后端命令目录包含 `category`、`capability_id`、`required_agent_tools`、`available`、`unavailable_reasons` 等字段。
2. `/continue`、`/status` 的可用性由 Agent tool descriptor 与静态 adapter 两层共同判定。
3. 若某个公开 Agent 命令缺少必需工具，后端 `public_command_names` 不再暴露它，并在该命令条目中给出不可用原因。
4. 前端规范化后端目录时保留能力/可用性字段，候选列表只展示 `public && available` 的命令。
5. 旧隐藏命令仍可被 parser 识别，用于兼容迁移。

## TDD 计划

1. 后端 RED：新增 focused tests，验证命令目录会标记 Agent 控制命令的 required tools，并在 adapter 缺失时隐藏公开命令。
2. 前端 RED：扩展 `chatCommands.test.ts`，验证不可用公开命令不出现在候选里，但仍保留定义元数据。
3. 后端实现：新增 writing-agent service 层目录 builder，组合 core registry、tool descriptor、static adapter names。
4. 前端实现：扩展命令类型和 normalize/filter 逻辑。
5. T0/T1 验证：只跑命令目录、dialog endpoint、前端命令相关 vitest 与 typecheck。

## 分层验证

- T0: `pytest backend/tests/test_agent_command_catalog.py -q`
- T1: `pytest backend/tests/test_dialogs.py -k "chat_command" -q`
- T1: `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/views/HermesView.test.ts src/stores/chat.workspace.test.ts`
- T1: `.\node_modules\.bin\vue-tsc.cmd --noEmit`
- T0: `git diff --check`

## 非目标

- 不新增可执行斜杠命令。
- 不改变 `/continue`、`/status` 的最终 routing 行为。
- 不引入外部 agent 框架依赖。
- 不跑完整后端/前端测试套件，除非本阶段改动外溢。
