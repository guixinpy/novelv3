# Implement · L3 自治验证

## 当前状态

M3 所有代码就绪：
- `guards.py` — 五级循环风险检测（L1-L5）
- `budget.py` — 迭代+令牌预算 + refund
- `compaction.py` — 上下文用量预检
- `approval.py` — 审批门（三级权限）
- `check_chapter_quality` 工具
- Guard tripped → 恢复建议注入（harness.py:180-187）

## 验证脚本

`scripts/l3_verify.py` — 驱动 v2 sessions API 完成：
1. 逐章生成 10 章（每章一个 turn）
2. 自动处理审批
3. 护栏熔断检测
4. 上下文警告收集
5. 乒乓熔断测试

## 执行方式

```bash
# 启动后端
cd backend && uvicorn app.main:app --reload

# 运行验证（需要预创建项目）
python scripts/l3_verify.py --project-id <PROJECT_ID>
```

## 已知限制

- 批量 follow-up 队列驱动机制未实现（M3 路线图标注为 follow-up 队列驱动，但只有 guard recovery 会注入 follow-up）
- 上下文压缩在当前架构中是预检机制（warning），不是自动执行
