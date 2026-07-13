# M3 技术设计

## 1. guards.py — 五级风险检测

Hook 位置：`loop.py` 的回合引擎中，每次工具调用完成后检查。

```python
class GuardResult:
    tripped: bool
    level: str          # L1-L5
    reason: str
    diagnosis: dict

class GuardSystem:
    def __init__(self):
        self.history: list[dict] = []  # 当前回合的工具调用/响应记录
    
    def record_tool_call(self, name, args, result):
        """每次工具执行完记录一次"""
    
    def check(self) -> GuardResult | None:
        """五级检测按顺序执行，命中即返回"""
```

### 五级定义

| 级别 | 名称 | 检测逻辑 | 阈值 |
|------|------|---------|------|
| L1 | generic_repeat | 连续 N 次相同工具+相同参数 | ≥3 |
| L2 | ping_pong | A 工具结果触发 B 工具，B 结果又触发 A，循环 ≥2 次 | ≥2 对 |
| L3 | poll_no_progress | 同一工具连续调用且结果相似度 > 90% | ≥4 次 |
| L4 | unknown_tool_repeat | 模型持续请求不存在的工具 | ≥2 次 |
| L5 | global_fuse | 总迭代次数超过配置上限 | max*2 |

### 在 Loop 中的集成

```python
# loop.py run_turn 内
guards = GuardSystem()  # 每个回合新建

for tool_call in response.tool_calls:
    result = await _execute_one(...)
    guards.record_tool_call(tool_call.name, tool_call.arguments, result)
    trip = guards.check()
    if trip:
        await emit(GuardTripped(level=trip.level, reason=trip.reason, diagnosis=trip.diagnosis))
        stop_reason = StopReason.GUARD_TRIPPED
        break
```

## 2. 预算 refund

当前 `IterationBudget` 已有 `refund()` 方法。集成到 `_execute_one`：

```python
# loop.py _execute_one 内
if tool_def.permission in (PermissionLevel.READ,):
    # 只读工具 → 不消耗迭代预算
    budget.refund()  # consume 已在 run_turn 循环开头执行
```

注意：需要将 `budget` 引用传入 `_execute_one`。

## 3. 上下文压缩

新文件 `agent/compaction.py`：

```python
async def check_context_usage(history: list[dict], threshold=0.75) -> ContextWarning | None:
    """估算当前 tokens 占 max_tokens 的比例，超阈值发出警告事件"""

async def compact_history(history: list[dict], head_lines=2, tail_lines=10) -> list[dict]:
    """保留系统提示+开头 N 条+结尾 N 条，中间摘要为一条 user 消息"""
```

集成到 harness 的 `_run_one_turn` 中，在每次 LLM 调用前检查。

## 4. check_chapter_quality 工具

注册到 `tools/chapters.py`，permission=read：

- 检查字数是否在合理范围（<500 → 太短，>50000 → 太长）
- 检查标题是否为空
- 检查正文中是否有大纲偏离标记
- 返回质检报告

## 5. 批量模式

利用 harness 已有的 `follow_up` 队列机制。每章之间插入 `guard_check_tool` 检查点：

```python
# 在 harness.send() 中
for chapter_index in range(start, end):
    # 注入"写第 X 章"的 follow-up
    harness.queue_follow_up(f"请写第 {chapter_index} 章")
    # 每章后插入一个 guard checkpoint
```

## 6. 新事件

```python
@dataclass(frozen=True)
class ContextWarning:
    usage_pct: float
    total_tokens: int
    max_tokens: int

@dataclass(frozen=True)
class GuardTripped:
    level: str
    reason: str
    diagnosis: dict
```
