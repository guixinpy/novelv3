# P1 生成模式统一到 v2 + prompting 全链淘汰 · 技术设计

## 目标架构

```
一次性生成统一为「内联提示词 + provider.complete」：
  core/chapter_generation.py   章节生成（修订再生成/v2 动作）
  core/dialog_prompts.py       athena/hermes 聊天
  core/prompt_budget.py        上下文预算截断纯函数（原 budgeter，功能保留）
  backend/prompts/*.txt        保留 4 个活跃模板（generate_chapter/chat_hermes/chat_athena/compact_dialog_context/diagnose_project），
                               由 core 模块直接读文件渲染（去掉 registry/renderer 中间层）
  删除：app/prompting/ 全包 + 6 个死亡模板文件
```

## D1. core/prompt_budget.py（原 budgeter 功能迁移）

```python
def apply_context_budget(blocks: list[dict], max_chars: int) -> tuple[list[dict], dict]:
    """按 priority 排序截断，返回 (保留块, {omitted_keys, truncated_keys, requested_chars})。
    行为与 PromptBudgeter.apply 完全一致（200 章实验上下文管理关键）。"""
```
- 从 `prompting/budget.py` 迁移 `apply` + `_block_content`；contracts.PromptBudgetReport 内联为 dict。
- 新增测试：超长 Setup 块截断 + TRUNCATED 标记 + priority 保序（复用 test_prompting_contracts 的 budgeter 用例语义）。

## D2. core/chapter_generation.py（章节生成提示词内联）

- 迁入（从 `prompting/providers/chapter.py`）：`build_chapter_prompt_variables`、
  `build_chapter_prompt_context_blocks`、`build_chapter_trace_context_blocks`、
  `chapter_max_tokens`、常量（CHAPTER_CONTEXT_CHAR_BUDGET 等）。
- 渲染：`generate_chapter.txt` 由本模块直接读文件（`Path(__file__).parents[2] / "prompts"`）做
  `str.format(**variables)`（与原 renderer 同语义，验证 renderer 渲染方式后对齐）。
- 预算：上下文块走 `apply_context_budget`（D1）。
- `api/chapters._build_chapter_call_payload` 改调本模块（prompt_assembler 引用删除）。

## D3. core/dialog_prompts.py（dialog 提示词迁移）

- `prompting/providers/dialog.py` 全量迁移（624 行：athena/hermes 分支、world context 构建、
  上下文块、历史消息）。
- 渲染改造：`PromptAssembler.build(prompt_id, variables, context_blocks, messages)` 替换为：
  `_render_dialog_prompt(template_name, variables)`（直接读 prompts/*.txt + format）+ `apply_context_budget`。
- registry 的 prompt_id → template_name 映射内联（dialog.hermes→chat_hermes、dialog.athena→chat_athena）；
  required_vars 校验保留（缺失变量 KeyError 语义）。
- `dialog_utils._free_chat_reply` 改 import core.dialog_prompts（LLM 调用已是 provider.complete ✓）。

## D4. action_execution_service 修复（阶段 2 遗漏）

- generate_setup → `athena_ontology.generate_ontology` 同逻辑（stub 记录语义，与 athena 端点一致）
  ——改调 API 内部函数（避免 HTTP 依赖）：`athena_ontology` 的 stub 部分提取或直接调用端点函数。
- generate_storyline/generate_outline → `athena_evolution._execute_evolution_generate_tool`。
- 行为说明：v1 绞杀后「生成端点体系」全部是 control-plane 记录（execute_agent_api_tool stub），
  真实生成由 v2 agent 会话完成；action 动作对齐该语义（触发记录 + 查询现状数据）。
- 新增测试：3 个动作执行不抛 ImportError 且写运行记录。

## D5. 删除清单

- `app/prompting/` 全包：assembler/registry/renderer/budgeter/contracts/tracing/command_args/errors/providers/{chapter,dialog,athena,retrieval,longform,knowledge_base,few_shot,style}
- `backend/prompts/` 死亡模板：generate_outline/generate_setup/generate_storyline/athena_extract_l2/athena_world_model_semantic_check
  （athena_extract_l2 已被 l2 内联淘汰；semantic_check 仅 registry 注册无消费者）
- 测试：test_prompting_contracts、test_prompting_chapter_migration 删除；
  test_chapter_revisions 提示词断言更新；test_athena_dialog 等 import 更新。

## D6. 兼容与风险

| 风险 | 对策 |
|---|---|
| 渲染语义差异（renderer 的 format vs 内联 format） | 迁移后跑修订/聊天测试断言提示词内容关键片段 |
| budgeter 截断行为回归 | D1 测试复用原用例语义（priority/truncated 标记） |
| dialog 模板 required_vars 校验丢失 | 保留校验（KeyError 语义） |
| action 3 动作修复引入新依赖 | 只调 athena 端点内部函数（stub 记录），不引入 HTTP 调用 |
| 删除时遗漏引用 | grep app.prompting 归零断言 + 全量 pytest |

## 保留不变

- `create_or_replace_chapter` 同步 API 语义（provider.complete 已是 v2 路径）
- `chapters.generate` 端点与 `execute_agent_api_tool` stub：单独记录待决策（不在本次）
- v2 会话/内核/T1-T7 成果
