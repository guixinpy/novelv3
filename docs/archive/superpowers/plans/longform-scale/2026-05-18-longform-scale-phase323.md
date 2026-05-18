# Phase 323 - 写作诊断可执行建议

## 目标

将批量写作任务已经聚合的字数偏差与生成后维护警告，进一步转换为前端可直接展示的结构化处理建议。这样千章级长任务完成后，用户不只看到“有多少异常”，还能立即知道优先处理什么。

## RED

新增/扩展测试：

- `backend/tests/test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics`
  - 要求任务结果包含 `generation_diagnostic_recommendations`。
  - 覆盖偏短章节、偏长章节、生成后维护警告三类建议。
- `backend/tests/test_background.py::test_get_background_task_compact_includes_generation_diagnostics`
  - 要求 compact 后台任务接口保留建议列表。

初次运行结果：2 个测试按预期失败，失败原因是生产代码尚未写入或透传 `generation_diagnostic_recommendations`。

## GREEN

实现内容：

- `backend/app/api/writing.py`
  - 在 `_record_generation_diagnostics()` 中随诊断同步生成 `generation_diagnostic_recommendations`。
  - 按固定顺序输出建议：偏短章节、偏长章节、生成后维护警告。
  - 建议包含 `kind`、`severity`、`title`、`message`、`chapter_indexes`。
- `backend/app/api/background_tasks_api.py`
  - compact 结果保留 `generation_diagnostic_recommendations`，供前端轻量轮询使用。

## 阶段验证

已通过：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics backend\tests\test_background.py::test_get_background_task_compact_includes_generation_diagnostics -q
```

结果：`2 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_background.py -q
```

结果：`62 passed`

## 后续

下一阶段建议把 recommendations 接入前端 store 与 Hermes 仪表盘，让用户在批量写作任务完成后直接看到“建议处理”列表。
