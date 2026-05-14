# Phase 130: 长篇上下文检索降级可见性

## 背景

章节生成会注入长篇记忆上下文，长篇上下文中还会尝试按用户反馈构建 query-aware 检索证据。
此前该检索链路异常时会被静默吞掉，生成仍会继续，但 prompt 与上下文包都无法显示“本次缺少检索证据”。

对百万字、千章级写作来说，这类静默降级会削弱稳定性：

- 用户无法判断本章生成是否真正使用了检索证据。
- trace 中缺少诊断信息，不利于定位检索索引、向量库或源数据异常。
- 失败时容易被误判为模型质量波动。

## 修复

- 在 `build_longform_context_package` 的 query-aware 检索异常分支中加入 `query_aware_retrieval_warning` 诊断 section。
- 在 prompt context 中加入中文降级提示：`检索证据暂不可用，已跳过本次相关证据注入。`
- 不向 prompt 泄露原始异常消息，只保留 `error_type` 供结构化诊断使用。
- 保持章节生成不中断。

## 验证

- 先新增失败测试：
  - `backend/tests/test_longform_scale.py::test_longform_context_marks_query_retrieval_failure`
  - RED：当前实现没有 `query_aware_retrieval_warning`。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_context_marks_query_retrieval_failure -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`

## 后续观察

- 若后续 trace 面板展示长篇上下文 section，可将该诊断段以“检索降级”状态高亮。
- 章节生成主链路已有独立 retrieval provider error trace，本次修复补齐的是长篇记忆内部 query-aware 检索的可见性。
