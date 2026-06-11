# 05 · 进度追踪

> 每次 session 开始先读本文档，结束前更新本文档。只追踪活跃工作；完成的里程碑折叠为一行。

## 当前状态

- **阶段**：M0 完成，M1 进行中
- **分支**：`claude/agent-refactor`
- **最近更新**：2026-06-11

## 已完成

- ✅ 2026-06-11 仓库克隆、工作分支建立、旧 codex-guide 归档、参考快照更新、全库勘察、claude-guide 编写
- ✅ 2026-06-11 **M0 完成**：
  - `app/agent/providers/`：Provider 抽象 + DeepSeekProvider（原生 function calling、SSE 流式、分片重组、重试归一化、用量统计），TDD 10 测试
  - `app/agent|tools|domain` 骨架 + 依赖方向规则测试（`tests/agent/test_dependency_rules.py`）
  - 保留模块回归独立可跑（world_checkers / athena_retrieval / world_proposals，125 测试）
  - `scripts/verify_refactor.sh`（kernel|kept|all 三模式）
  - 退出标准验证：全量 1766 passed（基线 1753 + 新增 13）

## 进行中

- 🟡 M1 · 最小可用 Agent 内核（loop / harness / registry / 首批只读工具 / budget / v2 API）

## 下一步

1. `tools/registry.py` + `@tool` 装饰器 + 权限三级（TDD）
2. `agent/loop.py` 无状态回合引擎 + 事件 sink（TDD）
3. `agent/budget.py` 迭代/令牌预算
4. `agent/harness.py` 会话状态 + JSONL 日志
5. 首批只读工具 + `/api/v2/sessions` 最小实现

## 问题清单（dogfood / 评审发现，修复优先于新功能）

（空）

## 阻塞 / 待用户决策

- DeepSeek API key 可用性确认（M1 真实联调需要；fake provider 测试不受影响）
