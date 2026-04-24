# World Model Follow-up TODOs

- 日期：2026-04-21
- 主题：world model 第一轮落地后的非阻断后续项
- 状态：待办
- 关联提交：`fa5a80c`

## 目标

记录当前 world model 已落地但尚未扩展完成的事项，避免后续遗忘或重复讨论。

## P1

- 接入 `subject knowledge` 前端视图。
  - 当前前端只展示 `current truth`。
  - 需要补 API、store 和组件入口，让用户能切换查看“某主体认知”。

- 接入按章节 `snapshot` 前端视图。
  - 当前没有“截至某章”的世界状态回看能力。
  - 需要补章节选择、快照请求和只读展示。

- 补 proposal 审批的完整字段级 diff 编辑器。
  - 当前 `approve_with_edits` 只支持最小 `notes` 编辑。
  - 需要把允许编辑的字段做成结构化表单，并显示编辑前后差异。

## P2

- 给 proposal 列表增加分页。
  - 当前 bundle/item 列表全量加载。
  - 数据量上来后会拖慢页面，也不利于定位。

- 给 proposal 列表增加筛选。
  - 至少支持按 `bundle_status`、`item_status`、`profile_version` 筛选。

- 增加 proposal 冲突提示。
  - 当前只展示条目和 impact snapshot。
  - 需要把“与现有 truth 冲突”“与当前 profile 不一致”“高风险审批”显式标出来。

## P3

- 接入真实 reviewer 身份。
  - 当前前端统一写死为 `frontend.reviewer`。
  - 后续需要接真实用户/编辑身份，至少写入可审计的 reviewer 标识。

## 备注

- 以上事项都不阻断当前 world model 主流程使用。
- 下一轮优先顺序建议：`subject knowledge` -> `snapshot` -> `完整 diff 编辑器` -> `分页/筛选/冲突提示` -> `真实 reviewer 身份`。
