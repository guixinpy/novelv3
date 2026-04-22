---
title: World Model Follow-ups 设计文档
date: 2026-04-22
status: approved
relates_to: docs/superpowers/plans/2026-04-21-world-model-followups.md
---

# World Model Follow-ups 设计文档

## 概述

在 world model 第一轮落地（`fa5a80c`）基础上，补全 7 项后续功能。按优先级分 P1/P2/P3 三批实现。

## P1-1 主体认知视图

### 后端

新增端点：

```
GET /api/v1/projects/{project_id}/world-model/subject-knowledge?subject_ref=张三
```

- 查询 `WorldFactClaim` where `claim_status="confirmed"` AND (`subject_ref=X` OR `object_ref_or_value` 包含 X)
- 响应复用 `ProjectWorldOverviewOut` 结构，只含该主体相关数据
- 分两组返回：`as_subject`（作为主体）和 `as_object`（作为客体）

### 前端

- `WorldProjectionViewer` 改造为 3-tab 结构：当前真相 / 主体认知 / 章节快照
- "主体认知" tab 下加主体下拉选择器，数据源从 `projection.entities` 提取
- 内容分两栏展示：作为主体的事实 / 作为客体的事实，复用现有卡片样式
- Store 新增 `subjectKnowledge` state + `loadSubjectKnowledge(projectId, subjectRef)` 方法

## P1-2 章节快照视图

### 后端

新增端点：

```
GET /api/v1/projects/{project_id}/world-model/snapshot?chapter_index=5
```

- 复用 `world_projection.py` 投影逻辑，加 `chapter_index <= N` 上界过滤
- 响应复用 `ProjectWorldOverviewOut` 结构
- 章节列表从项目已有章节数据获取

### 前端

- "章节快照" tab 下加章节选择器：前后翻页按钮 + 章节数字
- 虚线边框 + "只读快照" 标记，视觉上区分于当前真相
- 内容布局复用实体/事实/在场三栏结构
- Store 新增 `chapterSnapshot` state + `loadChapterSnapshot(projectId, chapterIndex)` 方法

## P1-3 完整字段级 Diff 编辑器

### 可编辑字段（7个，与后端 EDITABLE_CLAIM_FIELDS 一致）

| 字段 | 控件类型 |
|------|---------|
| `chapter_index` | 数字输入 |
| `intra_chapter_seq` | 数字输入 |
| `valid_from_anchor_id` | 下拉选择（timeline_anchors） |
| `valid_to_anchor_id` | 下拉选择（timeline_anchors） |
| `source_event_ref` | 文本输入 |
| `evidence_refs` | 标签输入（可添加/删除） |
| `notes` | 文本域 |

### 前端

- 新组件 `ProposalClaimDiffEditor.vue`，替换 ActionPanel 中的 notes textarea
- 点击"编辑后通过"时内联展开编辑器（非弹窗）
- 每行显示：字段名 | 原始值 | 编辑输入 | 重置按钮
- 变更字段自动高亮（黄色背景），顶部显示变更计数 badge
- 只将实际修改的字段收集到 `edited_fields` dict 提交
- anchor 下拉需从 timeline_anchors 数据填充

### 后端

无需改动 — `_validate_edited_fields()` 已支持完整 `EDITABLE_CLAIM_FIELDS` 验证。

## P2-1 Proposal 列表分页

### 后端

`GET /proposal-bundles` 新增 query params：`offset`（默认 0）、`limit`（默认 20）。

响应改为分页结构：

```json
{ "items": [...], "total": 85, "offset": 0, "limit": 20 }
```

### 前端

- `WorldProposalBundleList` 底部加"加载更多"按钮，显示已加载/总数
- Store 追加加载逻辑，累积 bundles 而非替换

## P2-2 Proposal 列表筛选

### 后端

`GET /proposal-bundles` 新增 query params：`bundle_status`、`item_status`、`profile_version`，均可选。

- `item_status` 筛选：返回包含匹配 item 的 bundles
- 筛选参数与分页参数组合使用

### 前端

- 列表顶部加筛选栏：三个下拉选择器 + "清除筛选"链接
- 切换筛选时重置 offset，重新加载

## P2-3 冲突提示

### 后端

Bundle detail 响应中新增 `conflicts` 字段：

```json
{
  "item_id": "xxx",
  "conflict_type": "truth_conflict" | "high_impact",
  "detail": "与现有真相冲突：张三.阵营 = 正派",
  "existing_claim_id": "yyy"
}
```

- 冲突检测：proposal item 的 `subject_ref + predicate` 与现有 confirmed truth 比对，值不同则标记 `truth_conflict`
- 高风险检测：`impact_snapshots.affected_truth_claim_ids` 数量 >= 3 则标记 `high_impact`

### 前端

- `WorldProposalItemCard` 显示冲突/高风险 badge
- 冲突项左侧红色边框 + 冲突详情文字
- 高风险项左侧黄色边框 + 影响数量提示

## P3 真实 Reviewer 身份

### 前端

- Store 新增 `reviewerName` state，默认 `"editor"`
- 持久化到 `localStorage`，key: `mozhou_reviewer_{projectId}`
- 设置入口：world model 面板顶部小齿轮图标，弹出输入框
- `WorldProposalActionPanel.emitReview()` 的 `reviewer_ref` 改为从 store 读取

### 后端

无需改动 — `reviewer_ref` 已是自由文本字段。

## 实现顺序

按 follow-up 计划建议：

1. P1-1 主体认知视图
2. P1-2 章节快照视图
3. P1-3 完整 Diff 编辑器
4. P2-1 分页 + P2-2 筛选（可并行）
5. P2-3 冲突提示
6. P3 真实 Reviewer 身份

## 文件变更范围

### 后端新增/修改

| 文件 | 变更 |
|------|------|
| `backend/app/api/world_model.py` | 新增 subject-knowledge、snapshot 端点；proposal-bundles 加分页/筛选参数 |
| `backend/app/core/world_projection.py` | 新增 chapter_index 过滤投影方法 |
| `backend/app/core/world_proposal_service.py` | 新增冲突检测逻辑 |
| `backend/app/schemas/world_proposals.py` | 新增分页响应 schema、冲突 schema |

### 前端新增/修改

| 文件 | 变更 |
|------|------|
| `frontend/src/components/world/WorldProjectionViewer.vue` | 改造为 3-tab 结构 |
| `frontend/src/components/world/WorldSubjectKnowledge.vue` | 新增：主体认知内容组件 |
| `frontend/src/components/world/WorldChapterSnapshot.vue` | 新增：章节快照内容组件 |
| `frontend/src/components/world/ProposalClaimDiffEditor.vue` | 新增：字段级 diff 编辑器 |
| `frontend/src/components/world/WorldProposalBundleList.vue` | 加分页、筛选栏 |
| `frontend/src/components/world/WorldProposalItemCard.vue` | 加冲突/高风险 badge |
| `frontend/src/components/world/WorldProposalActionPanel.vue` | reviewer_ref 改为从 store 读取 |
| `frontend/src/stores/worldModel.ts` | 新增 subjectKnowledge、chapterSnapshot、reviewerName state 和对应方法 |
| `frontend/src/api/client.ts` | 新增 subject-knowledge、snapshot API 调用 |
