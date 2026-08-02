# P1 stub 生成端点体系清理 · 技术设计

## 删除/保留矩阵（四视角评审论证）

| 对象 | 处理 | 依据 |
|---|---|---|
| execute_agent_api_tool + AgentApiToolRunResult（dialog_utils） | 删 | stub 硬编码 success，无审计价值；调用方全删后零引用 |
| 假错误管道（_raise_if_agent_generation_failed、_with_agent_metadata、错误码映射） | 删 | 全部死分支（评审工程视角） |
| chapters.generate 端点 | 删 | 无前端调用死端点 |
| generate_ontology（athena_ontology） | 删 | 前端组件零调用；store 方法删 |
| generate_evolution_plan + _execute_evolution_generate_tool（athena_evolution） | 删 | 同上 |
| action_execution_service 3 个 stub 动作 | 删 | app/ 下无生产调用方（仅测试） |
| WritingAgentRun 表/模型 | **保留** | 历史审计；前端不查表 |
| generate_chapter 动作 + create_or_replace_chapter | **保留** | 真生成路径（修订/v2 动作依赖） |
| GET 查询端点（get_evolution_plan/get_ontology 等） | **保留** | 前端读取依赖 |
| 前端 3 个生成方法（client/store） | 删/注释引导 | 组件零调用；AgentV2View 已存在 |

## 依赖关系

- dialog_utils 符号删除必须在 athena_*/chapters/action 引用清理后（或同步，分阶段 grep 复检）
- action_execution_service 的 execute() 分支删除后：label_map、动作清单（ACTION_LABELS 等）同步清理
- 前端 client.ts 与 stores 删除后：vitest 全量跑（组件测试若引用需改——已核实组件零调用）

## 风险

| 风险 | 对策 |
|---|---|
| 漏删引用导致 ImportError | 每阶段 `grep` 归零断言 + 全量 pytest |
| 前端删除后组件测试断裂 | 组件零调用已核实；跑全量 vitest 验证 |
| 误删真路径（generate_chapter/GET 端点） | 保留清单明确；删除时逐符号确认 |
