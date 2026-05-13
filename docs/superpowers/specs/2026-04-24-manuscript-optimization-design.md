# Manuscript 编辑器 + 自优化反馈闭环 设计文档

## 概述

为墨舟 AI Writer 添加 Manuscript 正文编辑器和自优化反馈闭环系统。用户在 Hermes 对话中生成章节后，跳转到 Manuscript 编辑器进行批注和修正，提交后返回 Hermes 由 AI 重新生成，同时自优化管线从用户反馈中提取写作规则和偏好调整，Athena 展示学习成果。

## 核心流程

```
Hermes 生成章节 → 显示跳转链接（不显示全文）
       ↓
Manuscript 编辑器（批注 + 修正）
       ↓
确认模态框（汇总 + 跳转提示）
       ↓
跳转回 Hermes → 自动发送修订消息
       ↓
后端：重新生成 + 规则提取 + 偏好微调
       ↓
Athena 自优化仪表盘展示学习成果
```

---

## 一、Manuscript 编辑器（前端）

### 1.1 布局

经典三栏布局，复用现有 AppShell 的 SubNav + ContentArea 结构：

- **左栏（SubNav）**：章节列表 + 修订统计（批注数/修正数）+ "提交修订"按钮
- **中栏（正文区）**：章节标题 + 正文内容，最大宽度 720px 居中，行高 1.8，适合长文阅读
- **右栏（批注摘要面板）**：200px 宽，可折叠，列出当前章所有批注和修正，点击可跳转定位到对应段落

### 1.2 批注交互

1. 用户选中一段文字
2. 选区上方弹出内联气泡（浮动定位），包含文本输入框和"保存"/"取消"按钮
3. 保存后：选中文字加黄色高亮（`#FEF08A`），气泡收起
4. 点击已有黄色高亮可重新打开气泡查看/编辑/删除批注
5. 右侧摘要面板同步显示新批注条目

数据结构（前端临时状态，提交前不持久化）：
```typescript
interface Annotation {
  id: string                // 临时 UUID
  paragraphIndex: number    // 段落索引（从 0 开始）
  startOffset: number       // 选区起始偏移
  endOffset: number         // 选区结束偏移
  selectedText: string      // 选中的原文
  comment: string           // 批注内容
}
```

### 1.3 修正交互

1. 用户直接编辑正文文字（contenteditable 段落）
2. 编辑完成后（blur 或 Enter），系统自动对比原文和修改后的文字
3. 修正部分显示为绿色高亮（`#BBF7D0`）：原文划线 + 新文字
4. 右侧摘要面板显示修正条目（"原文 → 新文字"）
5. 用户可点击修正条目撤销该修正

数据结构：
```typescript
interface Correction {
  id: string                // 临时 UUID
  paragraphIndex: number    // 段落索引
  originalText: string      // 原始文字
  correctedText: string     // 修正后文字
}
```

### 1.4 正文渲染

正文按段落（`<p>`）渲染，每个段落是一个独立的可编辑单元。段落索引从 0 开始，与后端 `ChapterContent.content` 按 `\n\n` 分割的段落一一对应。

段落状态：
- **原始**：无高亮，正常显示
- **有批注**：选区范围内文字加黄色背景
- **有修正**：原文划线灰色 + 新文字绿色背景
- **批注+修正可共存**：同一段落可以同时有批注和修正

### 1.5 提交流程

1. 用户点击左栏"提交修订"按钮
2. 弹出确认模态框，内容：
   - 标题："提交第 N 章修订"
   - 汇总列表：所有批注和修正，按段落顺序排列
   - 提示文字："确认后将跳转回 Hermes，AI 将根据您的反馈重新生成本章"
   - 按钮："确认提交" / "取消"
3. 确认后：
   - 将批注和修正打包为 revision payload
   - 路由跳转到 `/projects/:id/hermes`
   - 通过 chat store 自动发送一条修订消息

### 1.6 章节跳转

Hermes 生成章节后，聊天消息中显示跳转链接而非全文。点击链接路由到 `/projects/:id/manuscript?chapter=N`。

Manuscript 通过 URL query param `chapter` 自动加载对应章节。

---

## 二、Hermes 行为变更

### 2.1 章节生成消息

当前：生成成功后在聊天中显示完整正文。
改为：显示简短的成功消息 + 跳转链接。

消息格式：
```
第 N 章「{title}」已生成（{word_count} 字）
→ 前往编辑器查看
```

"前往编辑器查看"是一个可点击的链接，跳转到 `/projects/:id/manuscript?chapter=N`。

### 2.2 修订消息处理

从 Manuscript 跳转回来时，chat store 自动发送一条特殊消息：

```json
{
  "input_type": "revision",
  "chapter_index": 1,
  "annotations": [...],
  "corrections": [...]
}
```

后端收到后触发章节重新生成，注入用户反馈到 prompt。

---

## 三、后端 API 变更

### 3.1 新增数据模型

```python
class ChapterRevision(Base):
    id = Column(String, primary_key=True)
    chapter_id = Column(String, ForeignKey("chapter_contents.id"))
    project_id = Column(String, ForeignKey("projects.id"))
    chapter_index = Column(Integer)
    revision_index = Column(Integer)  # 第几次修订，自增
    status = Column(String, default="submitted")  # submitted / regenerating / completed
    submitted_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)

class RevisionAnnotation(Base):
    id = Column(String, primary_key=True)
    revision_id = Column(String, ForeignKey("chapter_revisions.id"))
    paragraph_index = Column(Integer)
    start_offset = Column(Integer)
    end_offset = Column(Integer)
    selected_text = Column(Text)
    comment = Column(Text)

class RevisionCorrection(Base):
    id = Column(String, primary_key=True)
    revision_id = Column(String, ForeignKey("chapter_revisions.id"))
    paragraph_index = Column(Integer)
    original_text = Column(Text)
    corrected_text = Column(Text)
```

### 3.2 新增 API 端点

**POST** `/api/v1/projects/{project_id}/chapters/{chapter_index}/revise`

请求体：
```json
{
  "annotations": [
    { "paragraph_index": 1, "start_offset": 0, "end_offset": 20, "selected_text": "...", "comment": "..." }
  ],
  "corrections": [
    { "paragraph_index": 2, "original_text": "寒风凛冽", "corrected_text": "山风拂过衣袂" }
  ]
}
```

处理流程：
1. 创建 `ChapterRevision` 记录（revision_index 自增）
2. 批量创建 `RevisionAnnotation` 和 `RevisionCorrection` 记录
3. 构建修订 prompt（注入批注和修正到章节生成 prompt）
4. 调用 AI 重新生成章节
5. 更新 `ChapterContent.content` 为新内容
6. 触发自优化管线（异步）
7. 返回新的章节内容 + 自优化反馈摘要

**GET** `/api/v1/projects/{project_id}/chapters/{chapter_index}/revisions`

返回该章节的所有修订历史。

### 3.3 修订 Prompt 注入

在现有章节生成 prompt 基础上，追加修订反馈段：

```
【用户修订反馈】
以下是用户对上一版正文的批注和修正，请在重新生成时充分考虑：

批注：
- 第2段："林远站在崖边..."一句 → 用户意见：这段描写节奏可以再柔和一点

修正（必须采纳）：
- 第3段："寒风凛冽" → 改为 "山风拂过衣袂"

请根据以上反馈重新生成本章正文。修正部分必须采纳，批注部分作为参考改进方向。
```

---

## 四、自优化管线（后端）

### 4.1 触发时机

每次章节修订完成后异步触发，不阻塞主流程。

### 4.2 规则提取（Rule-level）

调用 AI 分析用户的修正和批注，提取写作规则：

Prompt：
```
分析以下用户对 AI 生成小说的修订反馈，提取可复用的写作规则。

修订内容：
{annotations_and_corrections}

请输出 JSON 数组，每条规则包含：
- condition: 触发条件（如"环境描写段落"）
- action: 具体规则（如"避免使用套话式描写，用具体感官细节替代"）
- confidence: 置信度 0-1（基于证据充分程度）

只提取有明确模式的规则，不要过度推断。置信度低于 0.6 的不要输出。
```

提取的规则存入 `prompt_rules` 表，`rule_type = "learned"`，`hit_count = 0`。

### 4.3 偏好微调（Preference-level）

统计修正倾向，调整 `project.style_config` 参数：

- 用户多次缩短环境描写 → `description_density` 下调
- 用户多次增加对话 → `dialogue_ratio` 上调
- 用户多次批注"节奏太慢" → `pacing_speed` 上调

微调逻辑：每个维度维护一个计数器，同方向累计 3 次触发一次参数调整（±1），避免单次修订导致剧烈变化。计数器存在 `prompt_rules` 表中（`rule_type = "preference_counter"`）。

### 4.4 FewShotExampleLibrary 改造

将硬编码示例迁移到 `few_shot_examples` 表。用户的高质量修正（修正前后对比）可作为新的 few-shot example 存入，`rating` 字段标记来源（1.0 = 人工修正，0.5 = 初始示例）。

查询时优先使用高 rating 的示例。

### 4.5 自优化反馈

重新生成完成后，在 Hermes 对话中追加一条系统消息：

```
📝 自优化反馈：
- 从本次修订中学到 2 条写作规则
- 描写密度偏好已调整：3 → 2
```

---

## 五、Athena 自优化仪表盘

### 5.1 新增 Section

在 Athena 导航的"演化"分组下新增"自优化"section（key: `optimization`）。

### 5.2 仪表盘内容

三个区块：

**写作规则列表**
- 展示所有 `rule_type = "learned"` 的 prompt_rules
- 每条显示：规则内容、命中次数、创建时间
- 用户可启用/禁用单条规则（`priority = 0` 表示禁用）
- 用户可手动添加规则

**偏好趋势**
- 展示 5 个偏好维度的当前值和变化方向
- 简单的数值 + 箭头（↑↓—）展示

**学习日志**
- 时间线形式展示每次自优化的结果
- 每条记录：时间、来源章节、提取的规则数、偏好变化

### 5.3 数据来源

- 写作规则：`GET /api/v1/projects/{id}/prompt-rules?rule_type=learned`
- 偏好趋势：从 `project.style_config` 读取
- 学习日志：从 `prompt_rules` 表按 `created_at` 时间聚合，`rule_type = "learned"` 的记录即为学习事件

---

## 六、新增文件清单

### 前端

```
frontend/src/components/manuscript/
  ManuscriptEditor.vue        — 正文编辑区（contenteditable 段落 + 高亮渲染）
  AnnotationBubble.vue         — 内联批注气泡（浮动定位）
  AnnotationSummaryPanel.vue   — 右侧批注摘要面板
  RevisionConfirmModal.vue     — 提交确认模态框
  ChapterLink.vue              — Hermes 中的章节跳转链接组件

frontend/src/components/athena/
  OptimizationDashboard.vue    — 自优化仪表盘
  RuleListPanel.vue            — 写作规则列表（启用/禁用/添加）
  PreferenceTrend.vue          — 偏好趋势展示
  LearningLog.vue              — 学习日志时间线

frontend/src/stores/
  manuscript.ts                — Manuscript 状态管理（批注、修正、当前章节）
```

### 后端

```
backend/app/models/
  chapter_revision.py          — ChapterRevision + RevisionAnnotation + RevisionCorrection 模型

backend/app/api/
  revisions.py                 — 修订 API 端点

backend/app/core/
  revision_prompt_builder.py   — 修订 prompt 构建
  optimization_pipeline.py     — 自优化管线（规则提取 + 偏好微调）
  few_shot_db_library.py       — DB 驱动的 few-shot 示例库（替换硬编码）

backend/alembic/versions/
  xxxx_add_revision_tables.py  — 数据库迁移
```

---

## 七、不在本次范围

- 多人协作 / 并发编辑
- 富文本格式（加粗、斜体等）— 正文纯文本
- 修订版本间的 diff 对比视图
- 自优化规则的自动过期/衰减机制
- A/B 测试不同 prompt 变体
