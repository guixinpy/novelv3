# Implement · M2 清理收尾

## 执行清单

### 1. 引用链深度分析
- [ ] 对 58 个文件逐一标注：外部引用方、是否可安全删除
- [ ] 确认新架构已覆盖的能力清单
- [ ] 产出 A/B/C 分类表
→ 验证：分类表完整，每个文件有明确处置

### 2. 切断 v1 端点
- [ ] 删除 `api/dialogs.py` 及其路由注册
- [ ] 检查 `api/chapters.py`、`api/outlines.py` 对旧层的引用
- [ ] 删除或迁移 `api/athena_ontology.py`、`api/athena_evolution.py`
→ 验证：`pytest tests/ -q` 保持全绿

### 3. 提取必要模型
- [ ] 从 `services/writing_agent/` 提取仍在用的数据模型到 `app/models/`
- [ ] 提取仍在用的 schema 到 `app/schemas/`
→ 验证：import 不报错

### 4. 删除旧编排层
- [ ] `rm -rf backend/app/services/writing_agent/`
- [ ] 删除旧编排层专用测试文件
→ 验证：`git grep -E "intent_router|run_service|tool_descriptor" -- '*.py'` 零命中

### 5. 全量回归
- [ ] `pytest tests/ -q` 全绿
- [ ] `cd frontend && npm test` 全绿
- [ ] `cd frontend && npm run build` 无错误
→ 验证：730+ backend tests + 576 frontend tests

### 6. Commit
- [ ] 每个步骤独立 commit
- [ ] 最终 commit message: "feat: M2 cleanup — delete old orchestration layer"
