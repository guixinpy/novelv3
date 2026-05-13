# Athena Narrative Atlas Design

## Status

Approved in discussion on 2026-05-01.

This document captures the agreed design baseline for adding a narrative graph mode to Athena. It is a design spec, not an implementation plan.

## Goal

在 Athena 的「叙事脉络」中新增一个独立的「图谱」视图，用叙事脊柱树呈现全书结构。

图谱模式不替代现有文本视图。现有「时间线」「故事线」「章节」「伏笔」继续作为详细阅读和编辑入口；新图谱承担总览、伏笔审计和快速定位。

## Current Context

现有前端结构：

- `AthenaView.vue` 负责渲染 Athena 内部视图。
- `TimelineView.vue` 展示正式世界事件时间线；当事件为空时展示已有叙事规划的降级提示。
- `NarrativeWorkbench.vue` 展示故事线、章节结构和伏笔的文本列表。
- `athenaNavigation.ts` 当前叙事视图包括 `timeline / storyline / chapters / foreshadowing`。

现有数据来源：

- `athena.timeline`：正式 timeline anchors/events。
- `athena.evolutionPlan.outline`：章节规划、plotlines。
- `athena.evolutionPlan.storyline`：plotlines、foreshadowing。
- `project.chapters`：实际章节状态。

## Design Principles

- 主干必须清晰：作者打开图谱后先看到全书章节骨架，而不是一团关系网。
- 枝干可以自由生长：故事线、角色线、秘密线可以从任意章节段分出，不强迫所有线条进入固定泳道。
- 伏笔埋收必须清楚：伏笔从埋设点到回收点要有明确路径，未回收或信息不足要明显标记。
- 文本视图继续保留：图谱负责结构感和导航，文本页负责完整细节。
- 默认可读优先：使用确定性 SVG 布局，不依赖随机力导向图；刷新后节点位置应稳定。
- 渐进增强：先由前端整合现有数据生成图谱，不要求后端立即新增专用 graph endpoint。

## User-Facing Shape

「叙事脉络」新增内部视图：

```text
图谱
时间线
故事线
章节
伏笔
```

`图谱` 是叙事脉络的总览地图。它可以成为叙事区默认视图，但不改变其他视图的 URL 和功能。

### Layout

图谱采用三栏工作台：

- 左栏：图层开关、聚焦模式、图例。
- 中间：叙事脊柱树 SVG 画布。
- 右栏：选中节点详情、跳转入口、状态摘要。

窄屏下改为：

- 顶部工具条显示图层和聚焦模式。
- SVG 画布横向滚动或缩放适配。
- 节点详情作为下方面板或抽屉显示。

## Narrative Spine Tree

### Chapter Spine

章节主干是图谱的固定骨架。

- 章节按顺序沿竖向主干排列。
- 20 章以内默认逐章显示。
- 超过 24 章时按连续章节段聚合显示，例如 `第1-5章`、`第6-10章`。
- 已有正文的章节节点带状态标记；只有规划未写正文的章节保持轻量状态。
- 点击章节节点后，右侧显示章节标题、摘要、正文状态、相关故事线、相关伏笔，并提供跳转到「章节」文本视图的入口。

### Branches

故事线和重要叙事线作为枝干从章节主干分出。

- 每条 plotline 形成一条枝干。
- plotline 的 milestones 映射到章节主干上的对应 chapter。
- 枝干可以从主干左侧或右侧长出，布局根据已有枝干数量交错分布，避免全部堆在一侧。
- milestones 作为枝干上的节点显示标题和章节号。
- 点击故事线或 milestone 后，右侧显示类型、摘要、章节位置、关联章节，并提供跳转到「故事线」文本视图的入口。

### Foreshadowing Links

伏笔用独立的跨节点连线表示。

- 已回收伏笔：金色虚线，从埋设章节或埋设 milestone 连到回收章节或回收 milestone。
- 未回收伏笔：红色虚线或红色标签，终点停在当前最新章节或标记为“待回收”。
- 信息不足伏笔：灰色虚线，提示缺少埋设章或回收章。
- 悬停伏笔线时显示摘要、埋设章、回收章、状态。
- 点击伏笔线或标签后，右侧显示伏笔详情，并提供跳转到「伏笔」文本视图的入口。

## Controls

### Layers

左栏提供图层开关：

```text
章节主干
故事线枝干
伏笔埋收
角色/秘密线
正式事件
```

初始默认开启章节主干、故事线枝干、伏笔埋收。

### Focus Modes

聚焦模式用于快速审稿：

```text
全书结构
只看未回收伏笔
按故事线筛选
按角色/关键词筛选
正式事件覆盖
```

聚焦模式只改变可见和高亮状态，不改变底层数据。

### Detail Panel

右侧详情面板根据选中对象切换内容：

- 章节：标题、摘要、正文状态、相关故事线、相关伏笔。
- 故事线：名称、类型、milestones、覆盖章节范围。
- milestone：章节号、标题、摘要、所在故事线。
- 伏笔：埋设章、回收章、状态、跨度、关联对象。
- 正式事件：事件类型、章节、描述。

每类详情都提供对应文本视图跳转，不在图谱里承载全部长文本。

## Data Model

前端新增一个纯函数式 graph builder，把现有数据转成稳定图谱结构。

输入：

```text
AthenaEvolutionPlan | null
ChapterSummary[]
AthenaTimeline | null
```

输出：

```text
NarrativeAtlasGraph
```

核心结构：

```text
NarrativeAtlasNode
- id
- type: chapter | chapter_group | plotline | milestone | foreshadowing | event
- title
- summary
- chapterIndex
- chapterRange
- status
- sourceView
- sourceKey

NarrativeAtlasEdge
- id
- type: trunk | branch | foreshadowing | event_anchor
- from
- to
- status
- label

NarrativeAtlasGraph
- nodes
- edges
- metrics
- warnings
```

布局信息由 graph builder 或组件中的 deterministic layout helper 生成。节点 id 必须稳定，不能使用数组 index 作为唯一标识；当源数据没有明确 id 时，使用视图类型、章节号、标题摘要组合生成稳定 key。

## Empty And Degraded States

当没有叙事规划时：

- 图谱显示“尚未生成叙事规划”，并保留现有生成入口的语义。

当 timeline events 为空但 outline/storyline 存在时：

- 图谱仍可用 outline/storyline 生成章节主干和枝干。
- 右侧状态说明正式事件尚未生成。

当伏笔缺少埋设章或回收章时：

- 伏笔进入“信息不足”状态。
- 右侧详情列出缺失字段，不隐藏该伏笔。

当图谱节点过多时：

- 章节自动聚合。
- 枝干可按故事线筛选。
- 伏笔默认只显示异常和选中故事线相关项。

## Architecture

新增前端单元：

- `NarrativeAtlasView.vue`：图谱工作台容器。
- `narrativeAtlasGraph.ts`：从现有 Athena 数据生成图谱节点、边和 warnings。
- `NarrativeAtlasCanvas.vue`：SVG 画布，只负责渲染布局和交互事件。
- `NarrativeAtlasControls.vue`：图层开关和聚焦模式。
- `NarrativeAtlasDetailPanel.vue`：选中节点详情和跳转动作。
- `narrativeAtlasGraph.test.ts`：覆盖图谱构建规则。

`AthenaView.vue` 只负责把 `athena.evolutionPlan`、`project.chapters`、`athena.timeline` 传入图谱组件，不承担图谱推导逻辑。

导航新增 `narrative graph` view：

```text
/athena/narrative?view=graph
```

旧 URL 保持兼容。

## Interaction Rules

- 点击节点：选中节点并打开右侧详情。
- 点击伏笔线：选中伏笔。
- 双击章节节点：切到「章节」文本视图并定位对应章节，如果现有文本视图还不支持定位，先切换视图并在详情面板保留目标章节。
- 图层开关：更新可见层，不重建原始 graph。
- 聚焦模式：更新高亮和弱化状态，不删除节点数据。
- 键盘可达：节点和线标签必须能通过按钮或列表项访问，不能只有 SVG path 可点击。

## Visual Semantics

- 蓝色：章节主干。
- 绿色/青色/紫色：不同故事线或叙事枝干。
- 金色虚线：已回收伏笔。
- 红色：未回收、缺失回收点、异常跨度。
- 灰色：信息不足或暂不可判断。

颜色不能作为唯一信息来源；状态还需要文本标签或图例说明。

## Testing

Unit tests:

- graph builder 能从 outline chapters 生成稳定章节主干。
- plotline milestones 能映射到章节节点。
- foreshadowing 能生成埋设到回收的边。
- 未回收伏笔生成 warning 和异常状态。
- 缺少章节号的数据不会崩溃，并进入信息不足状态。

Component tests:

- `graph` 视图能在 Athena 导航中出现。
- 图层开关能隐藏和恢复对应 SVG/列表元素。
- 点击节点后详情面板显示正确内容。
- 没有 timeline events 但有 outline/storyline 时仍显示图谱。
- 无叙事规划时显示明确空态。

Build verification:

- `npm run test:unit -- narrativeAtlasGraph.test.ts NarrativeAtlasView.test.ts athenaNavigation.test.ts`
- `npm run build`

Browser verification:

- 在 20 章 dogfood 项目中打开 `/athena/narrative?view=graph`。
- 确认主干、故事线枝干、伏笔线、右侧详情、图层开关可用。
- 在窄屏下确认文本不重叠，画布可滚动或缩放。

## Non-Goals

- 不删除或替换现有文本视图。
- 不在第一版中提供图谱节点编辑能力。
- 不引入随机力导向布局。
- 不要求后端新增 graph endpoint。
- 不把 Athena 对话或待审提案混入叙事图谱默认层；后续可以作为独立图层扩展。

## Success Criteria

- 作者能在一个视图里看清全书章节主干。
- 作者能看出主要故事线从哪些章节分出、在哪些章节回到主干或进入高潮。
- 作者能看出伏笔在哪里埋、在哪里收、哪些仍未回收。
- 作者能从图谱跳回现有文本视图查看完整细节。
- 图谱在缺少正式 timeline events 时仍然可用，不退化成空页。
