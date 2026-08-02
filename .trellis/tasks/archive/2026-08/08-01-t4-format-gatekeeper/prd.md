# T4 输出格式守门员：格式校验 + 每章卡点

> 父任务：08-01-harness-optimization（design.md D1/D2）。来源：评审 P0-2（必做）、读者建议 2/7、交接方向 8。
> 背景：200 章实证——全角引号 ch31 起归零、`**` 渗入 5 章、`/` 备选词入正文、正文自带章题行 101 次、
> 第二部章末大量「继续往前走去」式无钩子结尾。全部是纯机械错误，护栏触发 0 次。

## Goal

给章节输出加「格式守门员」+「每章卡点校验」，让模型在格式漂移/无钩子收尾时被提示重写。
校验逻辑为确定性规则（轻量、低成本、可单测），不引入新依赖。

## Requirements

### R1. 新增 `check_chapter_format` 工具（read 权限，`tools/chapters.py`）
- 校验逻辑为纯函数，放新文件 `app/core/format_checker.py`；工具层薄封装。
- 五类检查（用评审实证构造测试样本）：
  1. **markdown 残留**：正文含 `**`（成对或单个）
  2. **备选词残留**：中文语境 `X/Y` 模式（`[一-鿿]{1,6}/[一-鿿]{1,6}`，如「刮去/凿掉」）
  3. **重复章题行**：正文开头（前 3 行内）出现「第 N 章　标题」行（`^第\s*\d+\s*章[\s　]+\S+$`）
  4. **全角引号不成对**：`“` 与 `”` 计数不等
  5. **半角标点混用**：中文相邻的半角 `,.;:?!`（`[一-鿿][,.;:?!]` 或反向）
- 返回 `issues` 数组（severity/type/detail/示例片段），`quality: "fail" | "pass"`；
  fail 时模型应重写该章。
- 规则阈值保守（design D 风险对策）：只报明确模式，不误伤正常文本。

### R2. 每章卡点校验（并入 check_chapter_format 或独立 `check_chapter_hook`）
- 检测章末无钩子收尾模式：结尾 100 字符命中已知「无钩子句式」列表
  （「继续往前走去」「望着那道光」「极静极稳地立着」「守着」「心里那句…落下」类），
  且结尾无对话引号 → 提示「本章结尾可能缺乏悬念/信息增量」。
- 与格式问题同返回体（不同 type）。

### R3. check_chapter_quality 不修改（既有工具行为保持）
- 新增独立工具而非扩展既有，避免影响既有断言。

## Acceptance Criteria

- [ ] `app/core/format_checker.py` 纯函数：五类格式问题各自检出（用评审实证文本构造 ≥8 用例）
- [ ] 卡点检测：对「继续往前走去」类结尾检出、对正常对话结尾不误报
- [ ] `check_chapter_format` 工具对坏章节返回 `quality: "fail"` + issues，好章节 `pass`
- [ ] 既有 check_chapter_quality 测试不受影响
- [ ] 后端全量 pytest 通过（622 基线只增不减）、前端 vitest 无回归
- [ ] 独立 commit（message 前缀 `harness: T4`）

## 实现要点（已核实代码位置）

- 新文件 `backend/app/core/format_checker.py`（纯函数：`check_text_format(text) -> list[issue]`、
  `check_chapter_hook(text) -> list[issue]`）
- `backend/app/tools/chapters.py` — 新增 `check_chapter_format` 工具（读 ChapterContent 后调纯函数）
- 实证样本（评审第 5 节）：
  - `**`：ch105「同**道理**一般/被人**亲手凿去了**」
  - 备选词：ch105「刮去/凿掉/磨平了」
  - 章题行：「第101章　漂来的小船」（正文开头自带）
  - 半角标点：ch2「睡不着,」、ch100「你今日不去局里了?」
  - 卡点：ch195「继续往前走去」
- 测试：`backend/tests/agent/test_tools_quality.py` 或新 `test_format_checker.py`（纯函数测试文件）

## Notes

- 只读工具；不改变既有工具行为。
- 规则写死正则，不引入 NLP 依赖。
