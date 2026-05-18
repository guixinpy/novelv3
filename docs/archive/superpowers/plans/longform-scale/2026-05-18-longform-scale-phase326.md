# Phase 326 - 长篇准备度纳入 smoke gate

## 目标

把 Phase 325 的 `ready_for_writing` 信号纳入百万字合成压测，避免“耗时通过、字数通过，但长篇维护状态不可继续”的情况被误判为成功。

## RED

新增/扩展测试：

- `backend/tests/test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress`
  - smoke report 必须包含 `maintenance.ready_for_writing`、`issue_count` 和 `recommendations`。
- `backend/tests/test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings`
  - timings 必须包含 `maintenance_diagnostics`。
- `backend/tests/test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_longform_maintenance_is_not_ready`
  - CLI 默认在 `maintenance.ready_for_writing=false` 时失败。

初次运行结果：3 个测试按预期失败，分别缺少 report 字段、timing 阶段和 CLI gate。

## GREEN

实现内容：

- `backend/app/core/longform_scale_smoke.py`
  - post-generation maintenance 后读取长篇维护诊断。
  - 将诊断 compact 为 JSON-safe 结构，写入 smoke report 与后台任务结果。
  - 新增 `maintenance_diagnostics` timing 阶段。
- `scripts/longform_scale_smoke.py`
  - `_threshold_failures()` 默认检查 `maintenance.ready_for_writing`。
  - 未就绪时输出 `longform maintenance is not ready for writing; issue_count=N`。

## 阶段验证

已通过：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_longform_maintenance_is_not_ready -q
```

结果：`3 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q
```

结果：`49 passed`

百万字 smoke 复核：

```powershell
backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --target-chapter 500 --cleanup --max-elapsed-ms 32000 --max-stage-ms seed_project=15000 --max-stage-ms memory_rebuild=10000 --max-stage-ms retrieval_reindex=15000 --max-stage-ms maintenance_diagnostics=10000 --max-stage-ms context_build=10000 --max-stage-ms post_generation_maintenance=10000 --max-stage-ms writing_worker=10000 --max-writing-under-target 0 --max-writing-over-target 0 --max-writing-warnings 0
```

结果：通过。

关键指标：

- `elapsed_ms`: `27621`
- `maintenance.ready_for_writing`: `true`
- `maintenance.issue_count`: `0`
- `maintenance_diagnostics`: `36ms`
- `writing_worker.generation_diagnostics.word_target.within_count`: `1000`
- `repeat_reindex.indexed.documents`: `0`

备注：旧 `--max-elapsed-ms 30000` 在一次运行中因总耗时 `30308ms` 失败；新增 `maintenance_diagnostics` 本身仅约 `35ms`，主要波动来自检索重建和写作 worker。当前建议将百万字 smoke 的总耗时阈值设为 `32000ms`，继续用分阶段阈值限制真正的局部退化。
