# 墨舟全站 UI 重构设计

- 日期：2026-04-17
- 主题：全站聊天中枢 + Inspector 重构
- 范围：项目列表页 `/`、项目详情页 `/projects/:id`、设置页 `/settings`
- 结论：采用“聊天中枢 + Inspector”方案，统一为重羊皮纸创作中枢视觉；项目详情页改为左侧主聊天区、右侧次级 Inspector；前后端围绕结构化 UI 状态协作

## 1. 目标与非目标

目标：

- 修正当前项目详情页“功能区压过聊天区”的主次错误，让对话成为绝对主入口。
- 将项目列表页、详情页、设置页统一到同一套视觉系统与页面壳层，消除割裂感。
- 用最小可用的结构化协议打通前后端，避免前端继续从 AI 文本里猜当前动作。
- 顺手整理页面装配、store 边界和刷新策略，降低后续扩展成本。

非目标：

- 第一轮不重做登录、鉴权、导出、后端生成链路和数据库结构。
- 不扩散到未在本设计范围内的次级页面。
- 不引入复杂富卡片协议或全新的实时通信机制。

## 2. 视觉方向

整体视觉采用“重羊皮纸创作中枢”：

- 基底为厚重黄褐色羊皮纸，不走冷白科技风，也不做廉价 AI 控制台。
- 文本主色使用深墨褐，强调色使用铜棕和深木棕，保留红黄绿状态色语义。
- 纹理只放在大背景和页面壳层，不进入高阅读密度区域。
- 正文消息区、输入区、设置表单区、版本 diff 区必须使用更干净的浅底，避免“脏、旧、裂”的道具感。

控制原则：

- “像羊皮纸，不像古董摊”。
- “像写作工具，不像品牌海报”。
- 美术表达必须服从阅读清晰度和交互效率。

## 3. 全站页面壳层

三类页面共享同一套 App Shell：

- 顶部导航：品牌、页面主路径、少量全局入口。
- 主容器：取消当前过窄的 `max-w-5xl` 限制，允许工作区在桌面端使用更宽布局。
- 背景层：统一重羊皮纸底色、轻纹理和阴影体系。
- 页面标题区：页级标题、摘要信息、少量上下文操作。

约束：

- 页面宽度策略由壳层统一管理，不允许页面自己各搞一套最大宽度。
- 配色、圆角、阴影、边框进入全局变量，不允许页面组件继续散装写色值。

## 4. 项目列表页

项目列表页从“普通卡片堆”升级为“项目矩阵 + 下一步动作”。

页面结构：

- 左侧主区：活跃项目卡片列表，突出项目阶段、当前状态、建议下一步。
- 右侧辅区：创作概况、推荐继续项目、快捷创建入口。

项目卡片信息：

- 项目名称、类型、当前阶段、当前字数。
- AI 建议下一步，例如“确认大纲”“继续正文修订”。
- 一眼能看懂是否值得继续进入该项目。

设计原则：

- 列表页的职责不是展示数据库，而是帮助用户决定“下一步先打开哪个项目”。
- 项目卡内容区比背景更干净，保持可读性。

## 5. 项目详情页

### 5.1 页面骨架

桌面端采用明确左右布局，推荐起始比例 `62 / 38` 到 `66 / 34`，实际以聊天区主导为准。

- 左侧主区：项目标题条、上下文条、消息流、快捷动作、输入区。
- 右侧次区：统一 `InspectorPanel` 容器。

要求：

- 输入区固定在左侧底部，消息流独立滚动，占满剩余高度。
- 右侧顶部仅保留轻量工具条：当前面板名、来源说明、模式开关、少量切换入口。
- 左右区独立滚动，禁止双滚动冲突。
- 移动端不强撑双栏，改为“上方聊天 + 下方抽屉式 Inspector”。

### 5.2 右侧 Inspector 模式

右侧只允许两种模式：

- `auto`：自动联动
- `locked`：锁定在某个面板

联动规则：

1. `auto` 模式下，右侧优先跟随用户最近操作和 AI 当前动作。
2. 用户点击章节、版本、快捷动作、手动切换面板，都会更新最近操作。
3. AI 进入明确动作时，右侧临时跳转到对应 Inspector，并显示来源文案。
4. `locked` 模式下，普通联动停止；关键动作允许临时跳转。
5. 临时跳转结束后，成功则回锁定面板；失败则停留在失败相关面板。

动作到面板映射：

- `preview_setup` / `generate_setup` -> `setup`
- `preview_storyline` / `generate_storyline` -> `storyline`
- `preview_outline` / `generate_outline` -> `outline`
- `chapter` / `deep_check` / `revise_content` -> `content`
- `version_diff` / `rollback_version` -> `versions`
- `topology` -> `topology`
- `preferences` / `style_feedback` -> `preferences`

左侧新增上下文条，持续显示：

- 当前查看的 Inspector
- 来源说明，例如“你刚点了第 3 章”“AI 正在生成大纲”

## 6. 设置页

设置页纳入统一壳层，不再像另一套系统。

页面结构：

- 左侧：模型配置、默认语言、生成策略。
- 右侧：说明区、风险操作区、重置入口。

要求：

- 表单区域保持更干净的浅底，优先保证输入可读性。
- 危险操作集中到低优先级区域，降低误触概率。
- 与工作区共享同一套视觉层级、留白和边框体系。

## 7. 前端状态架构

前端状态拆为三层：

### 7.1 `chat` store

职责：

- 消息流
- `pendingAction`
- 诊断信息
- 发送与审批 loading
- 后台完成轮询结果

### 7.2 `workspace` store

职责：

- `mode`: `auto | locked`
- `panel`
- `lockedPanel`
- `source`: `user | ai | system`
- `reason`
- `lastUserPanel`
- 临时跳转前的返回点

约束：

- 右侧焦点一律经 `workspace` store 变更。
- 页面和组件不允许私自改 Inspector 焦点。

### 7.3 `project` store

职责：

- 项目详情
- 设定、故事线、大纲
- 章节、版本、拓扑
- 偏好与设置类资源

约束：

- 只负责资源读写与缓存，不负责 UI 焦点计算。

## 8. 后端结构化 UI 提示

当前问题是接口只返回自然语言和部分状态，前端只能猜 UI 应该如何联动。第一轮在现有响应上新增最小字段：

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
    }
  },
  "refresh_targets": ["outline", "versions"]
}
```

字段含义：

- `dialog_state`：当前对话状态，例如 `CHATTING`、`PENDING_ACTION`、`RUNNING`
- `active_action.type`：当前动作类型
- `active_action.status`：如 `idle` / `pending` / `running` / `completed` / `failed`
- `active_action.target_panel`：建议联动的 Inspector 面板
- `active_action.reason`：供前端展示来源文案
- `refresh_targets`：本次操作后需要刷新的资源集合

第一轮必须补齐的接口：

- `sendChat`
- `resolveAction`
- `getBackgroundTask`

## 9. 数据流与刷新策略

新的协作路径：

1. 用户输入文本或点击动作。
2. 后端返回 `message + pending_action + project_diagnosis + ui_hint + refresh_targets`。
3. `chat` store 更新对话事实。
4. `workspace` store 根据 `ui_hint + 最近用户操作` 计算右侧焦点。
5. `project` store 仅按 `refresh_targets` 刷新对应资源。
6. `InspectorPanel` 渲染目标面板。

精准刷新要求：

- 生成设定后刷新 `setup`，必要时刷新 `versions`
- 生成故事线后刷新 `storyline`，必要时刷新 `versions`
- 生成大纲后刷新 `outline`，必要时刷新 `versions`
- 深度检查只刷新对应章节的检查结果或后台任务结果
- 版本回滚刷新 `versions` 和对应资源类型

禁止行为：

- 发送消息后无脑全量 `loadAllData()`
- 审批后无脑全量 `loadAllData()`
- 回滚后无脑全量 `loadAllData()`

## 10. 组件与文件边界

### 10.1 页面装配层

- `ProjectListView`：只负责列表页装配
- `ProjectDetailView`：只负责详情页装配，不再直接持有核心焦点状态
- `SettingsView`：只负责设置页装配

### 10.2 工作区组件

- `ProjectWorkspaceShell`：左右布局、响应式、滚动容器
- `ChatWorkspace`：上下文条、消息流、快捷动作、输入区
- `InspectorPanel`：右侧工具条与 Inspector 容器

### 10.3 Inspector 子组件

- `InspectorOverview`
- `InspectorSetup`
- `InspectorStoryline`
- `InspectorOutline`
- `InspectorContent`
- `InspectorTopology`
- `InspectorVersions`
- `InspectorPreferences`

约束：

- 各 Inspector 子组件只消费自己的领域数据，不跨区改焦点。
- 页面文件负责装配，store 负责状态，组件负责展示和本域交互。

### 10.4 样式边界

- 重羊皮纸主题变量进入全局样式系统。
- 页面组件只消费变量，不直接散写配色。
- 高阅读密度区域单独使用更干净的浅底 token。

## 11. 错误处理

失败态要同时体现在聊天区和 Inspector：

- 聊天区展示失败原因和动作状态变化。
- Inspector 保留在失败相关面板，方便用户查看上下文。
- `locked` 模式下，关键动作失败后停留在失败面板，不立即弹回锁定面板。
- 控制台报错、空白面板、错位滚动都视为缺陷。

## 12. 实施顺序

按以下顺序推进：

1. 后端补 `ui_hint`、`refresh_targets` 和动作到面板的映射
2. 前端新增 `workspace` store，统一焦点变更入口
3. 重做项目详情页工作区，完成左聊右 Inspector
4. 将项目列表页和设置页切入统一壳层与视觉系统
5. 用浏览器自动化回归真实页面和关键链路

## 13. 验收标准

- 项目详情页打开后，聊天区明显强于右侧功能区。
- 右侧 Inspector 在 `auto` / `locked` 两种模式下行为稳定。
- AI 生成、检查、回滚时，右侧跳到对应面板并解释原因。
- 列表页能明确展示“哪个项目最值得继续”和建议下一步。
- 设置页与工作区视觉一致，但表单区可读性不下降。
- 前端停止无脑全量刷新，只按目标资源局部刷新。
- 浏览器控制台无报错。
- 前端构建通过，后端测试通过。
