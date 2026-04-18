# 项目详情页 UI 重构设计

- 日期：2026-04-17
- 主题：聊天主导的项目工作区重构
- 范围：仅限项目详情页 `/projects/:id`
- 结论：采用 A 方案“沉浸式聊天”，桌面端左右布局，左侧主对话区，右侧混合模式工作区

## 1. 目标与非目标

目标：

- 修正当前详情页“工作区压过对话”的主次错误，让用户第一眼就知道对话是主入口。
- 保留右侧工作区，但降级为次级面板，默认联动、允许手动锁定。
- 让前后端围绕“结构化状态”协作，避免前端从 AI 文本里猜当前动作。
- 在不重写全站的前提下，提升详情页结构清晰度、可维护性和自动化联调效率。

非目标：

- 不重做项目列表页和设置页。
- 不改写现有生成链路、数据库模型和 AI 核心逻辑。
- 第一轮不新增复杂富卡片协议，只补最小可用的结构化 UI 提示。

## 2. 页面骨架

桌面端使用明确的左右布局，建议初始宽度比为 `68 / 32`。

- 左侧主区：项目标题条、对话上下文条、消息流、快捷动作、输入区。
- 右侧次区：单一 `InspectorPanel` 容器，不再保留一整列竖向大 Tab。

具体要求：

- 输入区固定在左侧底部，消息流独立滚动，占满剩余高度。
- 右侧顶部只有一条轻量工具条：当前面板名、来源说明、锁定开关、少量手动切换入口。
- 右侧主体根据当前焦点展示一个领域面板，例如设定、大纲、正文、版本。
- 移动端不强行双栏，改为“上方聊天 + 下方抽屉式工作区”。

## 3. 右侧工作区模式

右侧只允许两种模式：

- `auto`：自动联动。
- `locked`：手动锁定某个面板。

联动规则：

1. `auto` 模式下，右侧优先跟随用户最近操作。
2. “最近操作”来源包括：手动切换右侧面板、点击章节、点击版本、触发快捷动作、从对话中发起某类明确操作。
3. 当 AI 进入明确动作时，右侧临时跳转到对应面板，并显示原因。
4. `locked` 模式下，普通联动停止；但 AI 执行关键动作时仍可临时跳转。
5. 若 AI 在 `locked` 模式下触发临时跳转，动作结束后回到锁定面板。
6. 若动作失败，右侧停留在相关面板，展示失败上下文，不立即弹回。

建议的动作到面板映射：

- `preview_setup` / `generate_setup` -> `setup`
- `preview_storyline` / `generate_storyline` -> `storyline`
- `preview_outline` / `generate_outline` -> `outline`
- `chapter` / `deep_check` / `revise_content` -> `content`
- `version_diff` / `rollback_version` -> `versions`
- `topology` -> `topology`
- `preferences` / `style_feedback` -> `preferences`

左侧需要新增一个轻量“上下文条”，持续展示当前右侧焦点和来源，例如：`当前查看：正文 · 来源：你刚刚点了第 3 章`。

## 4. 前端组件与状态拆分

`ProjectDetail.vue` 仅作为页面装配层，不再承担全部逻辑。重构后拆为三层：

- `ProjectWorkspaceShell`：布局、响应式、滚动容器。
- `ChatWorkspace`：消息流、输入、快捷动作、审批卡片、上下文条。
- `InspectorPanel`：右侧统一面板容器。

右侧领域面板拆为独立组件：

- `InspectorOverview`
- `InspectorSetup`
- `InspectorStoryline`
- `InspectorOutline`
- `InspectorContent`
- `InspectorTopology`
- `InspectorVersions`
- `InspectorPreferences`

新增专门的 `workspace` store，只管理 UI 编排状态：

- `mode`: `auto | locked`
- `panel`: 当前面板
- `lockedPanel`: 锁定目标
- `source`: `user | ai | system`
- `reason`: 切换原因
- `lastUserPanel`: 用户最近操作面板

状态职责切分：

- `project` store：项目数据读取、缓存、资源刷新。
- `chat` store：消息、pending action、dialog state、loading。
- `workspace` store：右侧焦点计算、锁定状态、临时跳转。

约束：

- UI 焦点一律经 `workspace` store 变更，不允许组件私自改右侧面板。
- 组件以读取 store 为主，不做跨模块隐式写入。

## 5. 后端结构化提示

当前问题是前端过度依赖 `message` 文本，导致右侧跳转和刷新策略不稳定。后端需要在现有响应上新增最小结构化字段，保留旧字段兼容：

```json
{
  "message": "自然语言回复",
  "pending_action": {},
  "project_diagnosis": {},
  "ui_hint": {
    "dialog_state": "CHATTING",
    "active_action": {
      "type": "generate_outline",
      "status": "running",
      "target_panel": "outline",
      "reason": "AI 正在生成大纲"
    },
    "refresh_targets": ["outline", "versions"]
  }
}
```

字段约定：

- `dialog_state`：由后端给出当前对话状态，前端直接消费。
- `active_action.type`：动作类型，不靠 message 文本推断。
- `active_action.status`：如 `idle` / `pending` / `running` / `completed` / `failed`。
- `active_action.target_panel`：右侧建议跳转目标。
- `active_action.reason`：供前端展示来源文案。
- `refresh_targets`：指示前端仅刷新必要资源，替代当前“每次都全量重拉”的粗暴策略。

第一轮不要求所有接口都带完整结构，但以下链路必须补齐：

- 对话发送 `sendChat`
- 审批决策 `resolveAction`
- 后台任务查询 `getBackgroundTask`

## 6. 数据流与刷新策略

新的前后端协作路径：

1. 用户输入或点击动作。
2. 后端返回 `message + pending_action + project_diagnosis + ui_hint`。
3. `chat` store 更新对话事实。
4. `workspace` store 根据 `ui_hint` 和用户最近操作计算右侧焦点。
5. `project` store 仅按 `refresh_targets` 刷新相关资源。
6. `InspectorPanel` 渲染对应领域组件。

刷新策略要求：

- 设定生成后刷新 `setup`、必要时刷新 `versions`。
- 大纲生成后刷新 `outline`、`versions`。
- 正文深度检查后只刷新对应章节状态或后台任务结果，不全量刷新所有资源。

## 7. 错误处理

错误场景要统一：

- 左侧消息流展示失败原因。
- 若右侧是 AI 临时跳转面板，则保留在相关面板，方便用户查看失败上下文。
- 若后台任务失败，右侧面板需要能显示错误状态，而不是只有消息区一行报错。
- 控制台报错、空白面板、双滚动冲突都视为缺陷，不接受“功能能跑就行”。

## 8. 实施顺序

按以下顺序推进，避免大面积回归：

1. 后端补 `ui_hint` / `refresh_targets`。
2. 前端新增 `workspace` store 和 `ProjectWorkspaceShell`。
3. 将现有详情页 Tab 内容迁入 `InspectorPanel` 体系。
4. 调整视觉层级、滚动容器和移动端布局。
5. 用浏览器自动化回归核心链路。

第一轮改造只覆盖项目详情页，不顺手扩散到其他页面。

## 9. 风险与约束

主要风险：

- 状态源过多，右侧乱跳。
- 后端 hint 不稳定，前端继续猜动作。
- 布局调整后出现消息区、正文区滚动冲突。
- 移动端在双栏方案下直接失效。

处理原则：

- 右侧跳转统一经 `workspace` store。
- 后端显式维护动作到面板的映射表。
- 左右两区各自独立滚动。
- 桌面与移动端分别定义布局，不依赖一套样式硬扛。

## 10. 验收标准

- 打开项目详情页时，聊天区显著强于工作区。
- 用户手动切到某面板后，右侧保持稳定。
- AI 生成、检查、回滚时，右侧跳到对应面板并解释原因。
- 动作结束后行为符合 `auto` / `locked` 规则。
- 生成设定、生成大纲、章节深度检查三条链路前后端一致。
- 浏览器控制台无报错。
- 前端构建通过，后端测试通过。
