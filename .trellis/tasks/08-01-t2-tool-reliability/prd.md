# T2 工具可靠性：参数示例 + upsert 封装 + 情节线规范

> 父任务：08-01-harness-optimization（design.md D7）。来源：harness-engineering-list §一.2 + §二.3、评审 P0-3。

## Goal

工具层三段增强，减少模型因「参数不明 / 唯一约束 / 登记后找不到」三类错误产生的无效往返。

## Requirements

### R1. 参数校验错误加 few-shot 示例（`app/agent/tooling.py` `_validate_arguments`）
- 现状：错误信息只说「缺少必填参数 X / 类型错误」，不给正确写法。
- 要求：错误信息附加**参数示例 JSON**（从 parameters.properties 自动生成，只含 required 参数）：
  - 缺少必填参数 → `…请补全后重试。参数示例：{"chapter_index": 1}`
  - 类型错误 → `…收到 string。请改用正确类型重试。参数示例：{"chapter_index": 1}`
  - 未知参数 → 追加 `参数示例：…`
- 示例值生成规则：string→`"name"`（用参数名做示例文本）、integer→1、number→1.0、boolean→true、array→[]、object→{}。
- 生成函数为纯函数（如 `_example_arguments(parameters) -> dict`），可单测。

### R2. 写记忆类工具统一 upsert 封装（`app/core/longform_memory.py` 新增）
- 新增 `get_or_create_longform_memory(db, project_id, memory_type, scope_key, *, defaults=None, updates=None) -> LongformMemory`：
  先查（同 project+type+scope_key）→ 存在则应用 updates、不存在则按 defaults 创建；返回实例，调用方负责 commit。
- **重构接入点**（保持行为与提交点语义不变）：
  - `tools/memory.py` track_plotline open 分支（含 closed→reopen 的 status 处理）
  - `tools/memory.py` plan_arc define 的 story_arc upsert 分支
  - `tools/memory.py` 两处 arc_summary 写入（define 时与 progress 完成时）
  - `tools/chapters.py` `_capture_entities` 的 entity_state 写入
- 验收：以上 5 处均无重复的「查-建」手写逻辑。

### R3. 情节线登记与检索规范（`tools/memory.py` track_plotline）
- **open 登记校验**：
  - 标题长度 > 40 字符 → 拒绝，错误信息含命名模板：「弧名-目标」，示例「第一卷-寻找父亲-真相」
  - 标题含章节/卷/部序号（正则 `第[0-9一二三四五六七八九十百千万]+[章卷部]`）→ 拒绝，错误信息说明
    「标题不应携带章节/卷/部序号」（200 章实验暴露：标题带「第139章线·第二部…」导致后续检索必然失败）
- **query 检索增强**（只改 query，close 保持精确匹配防误关）：
  - title 提供时：精确 → 前缀 LIKE → contains LIKE 三级回退
  - 全部未命中 → 回退最近创建的开放 plotline，返回体附 `fallback: true` 与 `fallback_note`
- 现有测试 `test_track_plotline_open/close/reopen/query` 必须保持通过（行为兼容）。

## Acceptance Criteria

- [ ] 参数校验错误含「参数示例：{...}」且示例值类型正确（新增 ≥3 用例）
- [ ] `get_or_create_longform_memory` 存在，5 处接入点重构完成，现有测试全绿
- [ ] 超长/含章号 plotline 标题被拒绝（新增用例断言错误信息含模板建议）
- [ ] query 前缀匹配命中、contains 回退命中、全未命中 fallback 返回最近开放线（新增 ≥3 用例）
- [ ] 后端全量 pytest 通过（604 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T2`）

## 实现要点（已核实代码位置）

- `backend/app/agent/tooling.py:80-100` — `_validate_arguments`
- `backend/app/core/longform_memory.py` — 新增封装函数（文件已 1020 行，函数追加）
- `backend/app/tools/memory.py:42-91`（open 分支）、`:338-367`（arc upsert）、`:317-337`/`:446-457`（arc_summary）
- `backend/app/tools/chapters.py:106-125`（_capture_entities）
- 测试：`backend/tests/agent/test_tooling.py`、`test_tools_memory.py`

## Notes

- 不改变工具权限与事件契约；错误信息保持「写给模型看」风格。
- R2 封装不改变已有工具返回体结构（reopened/already_exists 等 action 值保留）。
