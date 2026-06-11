# 06 · 架构决策记录（ADR）

新决策从 CADR-001 开始编号。旧 ADR（`../archive/codex-guide/06-architecture-decisions.md`）逐条给出继承/推翻判定。

## 旧 ADR 处置表

| 旧 ADR | 决策 | 处置 | 说明 |
| --- | --- | --- | --- |
| ADR-001 | 对话驱动而非面板驱动 | ✅ 继承并强化 | 对话成为几乎唯一的工作入口 |
| ADR-002 | 世界观提案-审批门 | ✅ 继承 | 以 `propose` 工具权限 + approval 钩子形式重生 |
| ADR-003 | 工具三层（descriptor/adapter/execution） | ❌ 推翻 | 模板代码过重；改为装饰器自注册单层（CADR-003） |
| ADR-004 | 本地 hash 嵌入默认 | ✅ 继承 | M4 评估远程嵌入时重审 |
| ADR-005 | 进程内后台任务 | ✅ 继承 | 单用户场景足够 |
| ADR-006 | Profile 版本隔离 | ✅ 继承 | 防设定切换后旧事实泄漏 |
| ADR-007 | 请求泳道隔离 | ✅ 继承 | 前端机制保留 |
| ADR-008 | 参考项目不 vendor | ✅ 继承 | 仅提炼模式 |
| ADR-009 | AgentDefinition YAML | ⚠️ 搁置 | 脚本化 plan 删除后，是否还需要 agent 定义文件待 M2 后重审 |
| ADR-010 | Drawer Shell + Panel 拆分 | ✅ 继承 | 前端轨迹可视化保留 |
| ADR-011 | 能力切片 + 文件预算 | ✅ 继承 | 进入 `04-development-rules.md` |
| ADR-012 | 先框架后编码 | ✅ 继承 | 本文档集即其产物 |

## 新决策

### CADR-001 · 控制反转：模型驱动工具调用循环取代脚本化编排

**日期**：2026-06-11
**决策**：Agent 行为由「模型 + 工具目录 + 提示词 + 预算」涌现。删除意图路由、确定性 planner、预编排 step 序列。
**理由**：旧路径每新增能力需写三层模板与管线，复杂度线性膨胀且模型从未真正决策；三个参考项目（均为生产级 Agent）一致采用模型驱动循环。
**代价**：行为从确定性变为概率性，可靠性需由 M3 护栏重建——这是有意识的交换。

### CADR-002 · 保持 Python 技术栈

**日期**：2026-06-11
**决策**：不迁移 TypeScript/Rust。FastAPI + SQLAlchemy + Pydantic 保留。
**理由**：瓶颈在架构而非语言；可保留资产（world checker、retrieval、ORM、测试）全是 Python；最接近目标形态的参考（hermes-agent）也是 Python。TS 的全栈统一收益不抵数月迁移成本；Rust 与「快速迭代提示词/循环设计」的需求相悖。
**重审条件**：若未来出现多用户/高并发需求。

### CADR-003 · 工具 = 装饰器自注册 + 三级权限

**日期**：2026-06-11
**决策**：`@tool(name, schema, permission)` 装饰器，import 时自注册；权限 `read`（直接执行）/ `propose`（生成提案）/ `write`(过审批门)。
**理由**：hermes-agent 自注册模式 + 旧版审批门经验的折中。旧版「显式注册以便审计」的诉求由注册表统一校验 + 权限声明满足。

### CADR-004 · 会话双轨持久化：JSONL 日志 + DB 运行记录

**日期**：2026-06-11
**决策**：会话真相源是追加式 JSONL（openclaw 模式，支持断点恢复与压缩条目）；同时写 `WritingAgentRun/Step` 表供前端轨迹可视化与查询。
**理由**：JSONL 给恢复与调试，DB 给 UI 与统计；复用现有表避免前端重写。

### CADR-005 · 先通用内核、后领域专化的结构分界

**日期**：2026-06-11
**决策**：`agent/` 不含任何小说领域概念；领域知识只存在于 `tools/` 与 `domain/` 与提示词。
**理由**：用户路线「先合格 Agent、再网文专家」的结构保证；内核可独立测试，领域可独立演化。

### CADR-006 · DeepSeek 单 Provider 起步 + 传输层抽象

**日期**：2026-06-11
**决策**：Provider 抽象只定义格式转换接口（hermes ProviderTransport 模式），首发 DeepSeek，不预建多 provider 适配。
**理由**：抽象成本低（~150 行/provider），但 11 provider 迷宫是 hermes 明确的反面教材。
