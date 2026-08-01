# P1 v1 生成管线全面绞杀 · 技术设计

## 目标架构

```
统一 LLM 调用路径：
  provider.complete(messages, **kwargs) -> ProviderResponse
  ├── app/agent/providers/deepseek.py（DeepSeekProvider 实现，现有 stream 的收集封装）
  ├── api/dialog_utils.py（athena 聊天）
  ├── core/l2_extractor.py（一致性 L2）
  └── api/chapters.py create_or_replace_chapter（修订/v2 动作）

删除：core/ai_service.py、core/deepseek_adapter.py、core/chat_compaction.py、
      api/outlines.py generate/expand-window、api/setups.py generate、api/storylines.py generate、
      prompting/ 全目录（活跃内容迁出后）
```

## D1. Provider.complete 便捷方法

```python
# base.py
class Provider(ABC):
    async def complete(self, messages: list[dict], tools: list[ToolSpec] | None = None,
                       **kwargs) -> ProviderResponse:
        """非流式一次性调用（默认实现：收集 stream() 全部事件）。"""
        response: ProviderResponse | None = None
        async for event in self.stream(messages, tools=tools, **kwargs):
            if isinstance(event, ProviderResponse):
                response = event
        if response is None:
            raise ProviderError("provider stream ended without response", retryable=False)
        return response
```

- 迁移方调用 `provider.complete(messages, temperature=..., model=...)`（DeepSeekProvider
  的 `_build_payload` 已透传 kwargs：temperature/max_tokens/model）。
- 注：v1 的 `complete` 是**非流式一次返回**（DeepSeekAdapter），迁移后行为等价。
- `parse_json`（v1 提供）：迁移方用标准 `json.loads` + 现有 `parse_json_safely` 逻辑
  （deepseek_adapter 的 parse_json_safely 随删除 → 迁移到 `core/` 公共位置或各调用方内联；
  查引用面后决定——`core/json_utils.py` 或已有模块）。

## D2. 迁移点（保活优先）

### D2.1 dialog_utils（athena 聊天）
- `_free_chat_reply`：`AIService().complete(...)` → 模块级共享 `DeepSeekProvider` 实例
  （或每请求创建，参考现有 provider 生命周期：v2_sessions 用 `build_provider()`——
  dialog_utils 同样用 `build_provider()`，请求结束 `await provider.close()`）。
- dialog 模板（`prompting/providers/dialog.py` 624 行）→ 迁入 `api/dialog_utils.py` 内部
  （`_build_chat_call_payload` 已在 dialog_utils；模板函数合并进同文件）。

### D2.2 l2_extractor（一致性 L2，31 行）
- PromptAssembler 提示词 → 内联常量到 l2_extractor.py；
- `ai_service.complete` + `parse_json` → `provider.complete` + json 解析。

### D2.3 chapters.create_or_replace_chapter（修订/v2 动作）
- `_build_chapter_call_payload` 及其提示词链（chapter.py 模板）→ 迁入 `api/chapters.py`
  内部（或 `core/chapter_generation_prompt.py` 新模块——chapters.py 已 600+ 行，独立模块更清晰）；
- `ai_service.complete` → `provider.complete`；parse_json 同 D2.2。

### D2.4 纯函数/数据迁移（prompting 删除前置）
- `project_chapter_word_range` → `core/chapter_utils.py`（已存在模块，追加函数）；
  chapter_quality_review / longform_memory 改 import。
- `SetupContextSnapshot` + `build_setup_context_values` + `build_storyline_variables`
  + `normalise_json_text` → `core/setup_context.py`（新模块）；
  consistency / background_analyzer / world_context_assembler / dialog_utils 改 import。

## D3. 删除顺序与影响面

1. **迁移完成 → 验证全绿 → 删除**：
   - `core/ai_service.py`、`core/deepseek_adapter.py`、`core/chat_compaction.py`
   - 端点：outlines.py（generate/expand-window 段）、setups.py（generate 段）、storylines.py（generate 段）
     ——注意保留各文件的 CRUD（outlines GET/PATCH、setups GET、storylines GET 是基础读取）
   - `prompting/` 全目录（依赖检查：grep 确认零引用后删）
2. **测试清理**：
   - 删除：test_prompting_generation_migration、test_prompting_contracts、test_prompting_chapter_migration
     （迁移历史测试）、test_outlines/test_setups/test_storylines 中 generate 用例
   - 改造：test_chapter_revisions（修订再生成走 provider）、test_l2_extractor、test_config、test_topologies
     （mocking 从 AIService 换成 provider 或 DeepSeekProvider mock）
3. **兼容性**：chapters.py generate 端点（已 v2）与 CRUD 不动；v2 会话路径不动。

## D4. 风险与对策

| 风险 | 对策 |
|---|---|
| provider.complete 与 v1 complete 参数/行为差异（temperature/max_tokens 透传） | DeepSeekProvider._build_payload 已透传 kwargs；迁移后跑修订/聊天测试验证 |
| athena 聊天回归 | test 覆盖 _free_chat_reply（test_athena_dialog）先改后跑 |
| 删除 prompting 时遗漏引用 | 删前 grep 全仓 `app.prompting` 引用归零断言 |
| parse_json 逻辑丢失 | parse_json_safely 迁到 `core/json_utils.py`，引用方改 import（或内联，按引用面决定） |

## 保留不变

- chapters.py generate 端点（v2 agent tool 封装）
- 全部 CRUD API（前端基础读取）
- v2 会话/工具/内核（T1-T7 成果）
- `prompting/providers/style.py` 等若被 athena 引用需核实（当前 grep 显示仅 chapter.py 生成链用 → 随删）
