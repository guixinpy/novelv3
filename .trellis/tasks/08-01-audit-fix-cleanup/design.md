# Design · 审计修正收尾

## 1. 死代码删除清单（证据）

| 路径 | 文件数 | 证据 |
|---|---|---|
| `frontend/src/components/writingAgent/` | 58（30 vue + 28 test） | `rg "writingAgent" frontend/src --glob "!components/writingAgent/**" --glob "!**/*.test.ts"` 零命中；路由/视图无 import |
| `backend/app/core/chapter_compression.py` | 1 | `rg "chapter_compression" backend scripts` 仅命中自身 |
| `backend/app/core/chapter_expansion.py` | 1 | `rg "chapter_expansion" backend scripts` 仅命中自身 |
| `backend/test_support/writing_agent_run_helpers.py` | 1 | 无任何测试/代码引用；内部 import 指向已删除的 `app.services.writing_agent` |

删除策略：一次性删除并单独 commit，commit message 注明「死代码删除：58+2+1 文件」。

## 2. v2 轨迹持久化决策（CADR-004 修订）

现状：
- v2 会话：`AgentHarness` 写 `data/agent_sessions/<id>.jsonl` + `meta.json`（真相源、断点恢复、压缩条目）——已完成且被测试覆盖。
- `WritingAgentRun/Step` DB 表：仅 `dialog_utils.py`（athena v1 对话）创建；v2 循环不写。
- 前端：v2 页面（AgentV2View）直接消费 SSE 流事件，不查询 run/step 表；旧面板（已删）是唯一 DB 轨消费者。

决策：**修订 CADR-004 为「JSONL 单轨 + 可选 DB 投影」**——v2 会话持久化以 JSONL 为唯一真相源；`WritingAgentRun/Step` 保留为 athena v1 对话的兼容数据，不再要求 v2 写入，也不为其新建 UI。若未来需要统计/可视化，从 JSONL 投影，而非双写。

落地：在 `06-decisions.md` 的 CADR-004 条目追加修订说明（不改历史结论，新增日期）。

保留：`app/models/writing_agent.py`、`dialog_utils.py`、`frontend/src/api/types.ts` 中的 `WritingAgentRun*` 类型、`components/chat/recoveryAgentRunProjection.ts` 等 v1 兼容代码**不动**（athena 对话仍使用）。

> 注：`components/chat/agentRunProjection*`、`plannerAgentRunProjection.ts` 等是否依赖被删面板的导出，删除前以 `vue-tsc`/vitest 验证兜底。

## 3. .trellis agent-refactor 收尾

现状：18 个未提交文件（`.trellis/` 脚本/config/version 0.6.7→0.6.11，约 +1010/-187）。

步骤：
1. 冒烟验证：`python .trellis/scripts/get_context.py`（--mode phase/packages）、`task.py list`、`task.py current --json` 正常。
2. 独立 commit：`chore(trellis): agent-refactor 0.6.11 — dispatch auto + context injection + json outputs`。

## 4. 进度文档校准

`05-progress-tracker.md` 重写要点：
- 已完成条目按审计结果标注（L1-L3 通过、M5 工具集通过、测试数字属实、30 章属实）。
- 未完成/虚标条目修正：v2 轨迹 DB 轨未实现（已废弃）、v1 旧生成管线（ai_service + 8 API）仍存活、死代码残留已清理、M4 50 章未跑、M5 200 章未跑。
- 增加「2026-08-01 审计」小节记录方法与结论。

## 5. 提交与合并策略

顺序：
1. commit A：`.trellis` agent-refactor（独立主题）。
2. commit B：死代码删除。
3. commit C：CADR-004 修订 + tracker 校准（文档）。
4. 全量验证：pytest + vitest + `vue-tsc --noEmit`。
5. `git checkout main && git merge --ff-only claude/agent-refactor`，随后切回工作分支（main 与分支当前差 0/67，可快进）。

## 6. M4 50 章验证方案

复用 `scripts/l4_dogfood.py`（已支持 `--chapters 50`、`--project-id`）：
- 前置：uvicorn 服务运行，`.env` 含 DeepSeek key。
- 补充脚本能力（若缺失）：
  - 记忆问答断言：在特定章节后向会话提问「角色现在在哪/和谁在一起」，校验回复引用记忆工具结果。
  - 上下文排除检查：第 50 章请求时，从会话 JSONL 确认第 1-40 章正文未作为 system/user 原文注入（检查 harness 历史组装）。
- 运行方式：后台启动（Start-Process -WindowStyle Hidden），日志落盘，按 checkpoint 轮询。
- 结果记录：通过/失败/阻塞原因写入 tracker 问题清单与任务目录。

## 7. M5 200 章方案要点（输出文档）

- 前置：M4 50 章通过；明确质量趋势指标阈值（长度方差、重复度、一致性违规数）与采样方法。
- 实验设计：既有长篇续写（非新建项目），3-5 卷 × 40-60 章；每卷 checkpoint 记录 plan_arc/quality_trend/guard 数据。
- 成本与时长估算、失败判定与止损规则（质量下滑 → 停止诊断）。
