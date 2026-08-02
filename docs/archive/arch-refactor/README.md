# arch-refactor 归档（2026-08-02）

agent 架构重构（任务 08-02-agent-arch-refactor）过程中归档的代码。

## 已归档

### 阶段 0：自我优化实验链（learned PromptRule）

多轮重构遗留的「从用户修订中学习写作规则」实验功能——agent 写小说时自我优化反馈环，属实验演进产物，归档后修订流程不受影响。

| 原路径 | 归档位置 | 说明 |
|---|---|---|
| `backend/app/core/self_optimization.py` | `core/` | apply_revision_optimization：修订提交后写入 learned PromptRule |
| `backend/app/api/athena_optimization.py` | `api/` | learned rules 查询 API（GET /athena/optimization） |
| `backend/app/models/prompt_rule.py` | `models/` | PromptRule 表模型 |
| `backend/tests/test_self_optimization.py` | `tests/` | 对应测试 |

引用摘除：`api/athena.py`（router 注册）、`api/chapter_revisions.py`（2 处副作用调用）、`api/projects.py`（仅 import）、`models/__init__.py`（导出）、`tests/test_chapter_revisions.py` / `tests/test_projects.py`（learned rule 断言）。

验证：归档后旧后端 586 passed（原 590 - 4 归档测试）。

## 延迟归档（阶段 4 随旧后端整体清理）

- `core/world_*.py`（15 文件）+ `tools/world.py` + world 相关 models/schemas/api/tests —— world 提案系统（约 6k 行）。**延迟原因**：深度嵌入 12 个核心链文件（athena_longform 36 处引用等），提前摘除风险高；阶段 4 旧后端整体删除时随旧 core 一并归档，无需单独摘除。
- `core/revision_feedback.py` / `prompt_optimizer.py` / `writing_scheduler.py` —— 检查后确认属核心链（修订反馈格式化 / 风格规则翻译 / 写作调度），**保留不归档**。
