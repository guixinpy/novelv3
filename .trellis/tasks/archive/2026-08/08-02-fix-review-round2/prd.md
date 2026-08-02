# 修复二轮 code-review 9 项发现

## Goal

二轮 max 评审发现 9 项：审批事件双发/幂等键语义（先标记/锁外检查）/前端审批路径不匹配/审批占墙钟/event_id 非会话级/快照拼 system 违 KV 契约/会话注册表无淘汰/arc_summary 覆盖不完整

## Requirements

- TBD

## Acceptance Criteria

- [ ] TBD

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
