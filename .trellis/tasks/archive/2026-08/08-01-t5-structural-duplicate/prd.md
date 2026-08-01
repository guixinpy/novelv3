# T5 结构级重复检测：卷/弧线大纲相似度

> 父任务：08-01-harness-optimization（design.md D1/D2）。来源：交接方向 4、读者建议 4、评审 P2-7。
> 背景：第二部「换名城」副本连刷 4+ 次（沈水镇→未醒之城→更下游城→源头城），每座城 =
> 名字+树/针脚/水+一次性点破者，结构完全雷同；章题重复（「渡到底的是心」×3、「最初是谁」×3）。

## Goal

检测「情节结构级重复」（相邻 n-gram 抓不到、字符相似度抓不到的模板循环），提示模型换解法。

## Requirements

### R1. 纯函数检测模块 `app/core/structural_similarity.py`
- `detect_structure_repeats(chapters: list[dict]) -> list[dict]`，
  输入 `[{index, title, content}]`（工具层从 DB 构造），输出 issues。
- 两类检测（确定性规则）：
  1. **标题重复**：去标点规范化后相同且长度 ≥4 字符的标题出现 ≥2 次 → `title_repeat`
     （200 章实证：「渡到底的是心」×3、「最初是谁」×3、「欠我一条命」×2）
  2. **结尾指纹雷同**：每章结尾 120 字符去标点后两两字符重合率 > 0.75，
     互连成团 ≥3 章 → `structure_repeat`（200 章实证：ch160-201「望着水光/心里那句落下」式结尾）
- 字符重合率函数复用 guards._result_similar 的算法（字符级比对）。
- 输出：`{type, chapter_indexes, detail}`，detail 附「建议：更换冲突类型/人物关系/解法」。

### R2. 工具 `check_structure_repeat`（read 权限，`tools/chapters.py`）
- 参数：`window`（检查最近 N 章，默认 30，上限 60）。
- 查 ChapterContent 构造章节列表 → 调纯函数 → 返回 issues + `repeated: true/false`。
- 无数据/不足 3 章 → 提示数据不足（不报错）。

### R3. 阈值保守（父 design 风险对策）
- 标题重复：去标点后完全相同的才算（不做过模糊标题匹配，避免误报）。
- 结尾指纹：>0.75 高阈值 + ≥3 章成团才报；只提示不强制。

## Acceptance Criteria

- [ ] 3 章同标题 → title_repeat 检出（新增用例）
- [ ] 3 章结尾句式雷同（文字不同但结构相同）→ structure_repeat 检出（新增用例）
- [ ] 正常章节（不同标题不同结尾）→ 无 issues
- [ ] 不足 3 章 → 工具返回数据不足提示而非错误
- [ ] 后端全量 pytest 通过（635 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T5`）

## 实现要点（已核实代码位置）

- 新文件 `backend/app/core/structural_similarity.py`
- `backend/app/tools/chapters.py` — 新增 `check_structure_repeat`
- 相似度算法参考 `backend/app/agent/guards.py:31-41`（_result_similar）
- 测试：`backend/tests/agent/test_format_checker.py` 旁新增 `test_structural_similarity.py`

## Notes

- 只读工具；无新依赖；确定性规则。
- 「换名城」副本的检测信号：结尾句式指纹（点破→认回→望着水光），不依赖实体名（名字不同）。
