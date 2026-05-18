# Phase 325 - 长篇写作准备度与维护建议

## 目标

把长篇维护诊断从“计数展示”升级为“能否继续写”的可判定信号。用户在千章级写作前，需要快速知道章节记忆和检索索引是否可信，以及下一步该修复什么。

## RED

新增/扩展测试：

- `backend/tests/test_longform_scale.py`
  - 长篇维护诊断必须返回 `ready_for_writing`、`issue_count` 和 `recommendations`。
  - 覆盖过期章节记忆与过期检索索引两类建议。
- `frontend/src/components/athena/AthenaOverview.test.ts`
  - Athena 总览必须展示 `写作准备`、`问题` 和 `维护建议`。

初次运行结果：

- 后端定向测试因缺少 `ready_for_writing` 失败。
- 前端定向测试因未显示 `写作准备 需修复` 失败。

## GREEN

实现内容：

- `backend/app/core/longform_memory.py`
  - 维护诊断 payload 新增：
    - `ready_for_writing`
    - `issue_count`
    - `recommendations`
  - 根据缺失/过期章节记忆、缺失/过期检索索引生成结构化中文建议。
- `backend/app/schemas/longform_memory.py`
  - 新增 `LongformMaintenanceRecommendation`。
  - `LongformMaintenanceDiagnostics` 支持准备度与建议字段。
- `frontend/src/api/types.ts`
  - 同步长篇维护建议类型。
- `frontend/src/components/athena/AthenaOverview.vue`
  - 在长篇维护区展示写作准备、问题数和维护建议列表。

## 阶段验证

已通过：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_memory_after_chapter_edit backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_retrieval_after_memory_refresh -q
```

结果：`2 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q
```

结果：`48 passed`

```powershell
npm run test:unit -- --run src/components/athena/AthenaOverview.test.ts
```

结果：`9 passed`

浏览器烟测：

- URL: `http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/athena/overview`
- 结果：Athena 总览存在，页面包含 `长篇维护` 与 `写作准备`，非 favicon 资源错误和页面错误为 0。
