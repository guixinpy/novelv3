# Harness Engineering 改进清单（实验完成后执行）

> 方向：模型幻觉/行为偏差不可避免，优化重点是 harness 层——让内核在模型走偏时
> 能接住、纠正、恢复，并最大化模型能力发挥。参照 hermes-agent / openclaw /
> openhuman（研究见 `docs/claude-guide/m5-memory-research.md` 与归档任务）。

## 一、本次 200 章实验暴露的个例（已止血，需系统化）

### 1. 模型幻觉调用不存在的工具 → 请求 500 / SSE 断开
- 个例：`request_review`（第 85 章）
- 已做止血：`ApprovalGate.before_tool_call` 对未知工具返回友好错误（含可用工具清单）
- **系统化要求**：
  - `loop._execute_one` 对 `before_tool_call` 钩子自身异常兜底（hook 抛错不得崩循环）
  - `provider.stream` 的网络/协议错误分类：可重试（超时/断连）与不可重试（400 参数错），
    断连自动重试 1-2 次（带退避），仍失败则优雅结束回合并给模型诊断
  - 未知工具计数接入 GuardSystem（已有 L4 检测，验证 ≥2 次触发熔断）
  - 系统提示词明确“只能调用工具目录中的工具”，工具描述中避免与常见幻觉名混淆

### 2. track_plotline 重复 open 同 key → UNIQUE 冲突
- 个例：闭环后再 open 同一情节线
- 已做止血（待合入）：open 复用 closed 行重新打开
- **系统化要求**：所有写记忆类工具统一“upsert 语义”（open/define/create 先查后写），
  在工具层做唯一约束的通用封装（如 `get_or_create_longform_memory`）

### 3. 压缩摘要嵌套/信息丢失 → 模型压缩后“只规划不落笔”
- 已做止血：摘要跳过旧摘要、纳入最近写入/质量信息
- **系统化要求**：
  - 摘要内容向“可行动的写作上下文”倾斜：最近 3 章标题/字数/人物状态/开放线索，
    而非统计数字
  - 压缩阈值触发时保留 write_chapter 结果摘要（章节标题/字数）到 tail
  - 考虑“两级压缩”：确定性摘要（现）→ LLM 摘要（预算允许时，参照 hermes Frozen Snapshot）

## 二、参照开源项目的落地优先级（建议顺序）

1. **恢复闭环完善**（openclaw/harness 模式）：
   - 回合内工具错误 → 自动注入“错误诊断 + 下一步建议”到下一轮（已有 guard 触发版，扩展为通用版）
   - 会话级断点恢复：JSONL 已有；补“压缩后重放一致性”测试（已有 sanitize，补完整测试矩阵）
2. **上下文注入工程**（hermes Frozen Snapshot / openhuman hot-cold）：
   - 每回合注入固定“项目状态快照”（章节数、活跃弧线、最近 3 章标题、开放线索数），
     减少模型用工具探索的无效往返（200 章实测：模型频繁 list_chapters/get_project_state）
   - 记忆注入优先级与预算（已有 injection_limit，评估是否按回合动态调整）
3. **工具调用可靠性**：
   - 参数校验错误信息加“示例”（tooling 已有类型校验，补 few-shot 示例提示）
   - provider 重试/退避/错误分类（见上）
4. **质量护栏前移**：
   - write_chapter 前强制读最近章节（模型自发行为，可固化为 harness 检查：写入前 5 章未读
     则注入提醒），防止人物漂移
   - check_chapter_quality 结果纳入压缩摘要与质量趋势（已部分实现）
5. **可观测性**：
   - `analyze_dogfood.py` 已有：补“幻觉工具名统计”“未知工具频率”“每章质量自检结果”维度

## 三、执行时机

- 200 章实验完成 + 报告产出后开始
- 每项：先在 `backend/tests/agent/` 补测试，再改内核，跑全量 pytest/vitest，独立 commit
