# Design · M2 清理收尾

## 引用链分析

从评估 grep 结果，`services/writing_agent/` 的外部引用（非内部自引用）来自：

```
api/dialogs.py              → dialog_control_plane, run_service, slash_command_route
api/chapters.py             → (间接引用)
api/outlines.py             → (间接引用)
api/athena_ontology.py      → agent_definitions
api/athena_evolution.py     → agent_definitions
core/athena_retrieval.py    → slash_command_route
prompting/providers/chapter.py → (间接引用)
models/__init__.py          → (模型导入)
schemas/__init__.py         → (schema 导入)
```

## 删除方案

### Step 1: 分析并分类所有文件

将 58 个文件分为三类：
- **A 类 (死代码)**：无外部引用，可直接删除
- **B 类 (可迁移)**：功能已被新 `app/agent/` 或 `app/tools/` 覆盖
- **C 类 (需保留)**：仍在使用的纯数据模型/schema

### Step 2: 切断外部引用

对 B 类和 C 类文件的引用方：
1. `api/dialogs.py` → 整个文件删除（v1 端点，已被 v2 SSE 替代）
2. `api/athena_ontology.py` / `api/athena_evolution.py` → 评估是否可删除
3. `core/athena_retrieval.py` → 引用 `slash_command_route`，评估迁移
4. `models/__init__.py` / `schemas/__init__.py` → 提取必要的数据模型

### Step 3: 批量删除

```bash
rm -rf backend/app/services/writing_agent/
```

### Step 4: 修复测试

删除引用旧模块的测试文件，修复因导入消失而失败的测试。

## 回滚

每步一个独立 commit，出错 `git revert` 即可。
