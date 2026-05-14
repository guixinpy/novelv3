# Phase 131: 章节生成保留上一章末尾钩子

## 背景

章节生成 prompt 会注入 `上一章摘要`，用于承接上一章剧情。
此前摘要逻辑只截取上一章正文开头 300 字，长篇连载中常见的末尾反转、悬念、承接句会被截掉。

对千章级网络小说来说，这会直接影响连续性：

- 下一章可能接不上上一章末尾的悬念。
- 模型更容易重复前文铺垫，而忽略最新推进。
- 章节钩子与收束信息在长篇中权重不足。

## 修复

- 将上一章摘要预览从“只取开头”改为“开头 + 结尾”的固定预算片段。
- 保留原 300 字级别预算，不增加 prompt 膨胀风险。
- 短正文仍原样注入。

## 验证

- 先新增失败测试：
  - `backend/tests/test_chapters.py::test_chapter_prompt_previous_summary_keeps_ending_hook`
  - RED：旧实现只包含开头，不包含 `上一章末尾钩子`。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_chapter_prompt_previous_summary_keeps_ending_hook -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`

## 后续观察

- 如果后续引入章节摘要模型，可将“上一章末尾钩子”作为专门字段，而不是依赖正文截取。
- 当前修复优先解决稳定承接，不改变生成 prompt 的整体结构。
