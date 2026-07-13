# M1 dogfood verification

## Goal

验证 M1 Agent 内核能用真实 DeepSeek API 端到端跑通：通过对话让 Agent 自主调用 ≥2 个工具，给出有据回答。

## Prerequisites

1. DeepSeek API key 已写入 `.env`
2. 测试数据库有可用的项目、章节、世界观数据

## Plan

1. 运行 `seed_athena_e2e.py` 填充测试数据
2. 启动后端服务（uvicorn）
3. 通过 `/api/v2/sessions` SSE 接口发送对话消息
4. 观察 Agent 是否自主调用 ≥2 个工具
5. 验证回答是否准确有据

## Acceptance Criteria

- [ ] Agent 收到对话后发起 ≥2 次工具调用
- [ ] 工具调用类型覆盖 ≥2 种不同工具（如 query_world + read_chapter）
- [ ] Agent 最终回答引用了工具返回的数据，不是硬编码或空话
- [ ] SSE 流式事件序列完整（无断流、无超时）
- [ ] 会话可正常中断/恢复（写入 JSONL）
