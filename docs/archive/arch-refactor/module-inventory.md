# 归档模块清单（arch-refactor 后新架构不包含的模块）

按功能分组。归档代码位置：docs/archive/arch-refactor/（world/、legacy/、tests-legacy/、scripts/）；
git rm 的旧代码可从 git 历史恢复（commit 474a8f8c）。

## A. 世界模型提案系统（world_*，42 文件，~6k 行）
world_checker_registry、world_context_assembler、world_contracts、world_fact_scope、
world_projection、world_projection_service、world_proposal_*（service/state/records/review_queue/
resolution_apply/resolution_preview/agent_report）、world_replay、world_time_normalizer +
12 个 world 模型 + 4 schemas + 3 API（world_model/athena_evolution/athena_shared）+ tools/world

## B. 自我优化实验链（learned PromptRule）
self_optimization（修订反馈→学习规则）、athena_optimization（规则查询）、prompt_rule 模型

## C. 章节评审/修订链
chapter_continuity_review（连续性评审）、chapter_quality_review（质量评审）、
chapter_revision_planner/drafts/apply（修订规划/草稿/应用）、revision_feedback（批注格式化）、
cross_validator（交叉校验）、consistency_checker（一致性检查）、
checkers（Location/Timeline/Relationship/Foreshadowing 四检查器）

## D. 上下文装配与生成辅助
context_injection（上下文注入）、agent_context_compression_projection（压缩投影）、
continuity_anchor_proposals（连续性锚点）、setup_context/setup_projection（设定投影）、
writing_agent_constraints（写作约束）、model_call_trace（调用追踪）、
generation/blocks_*（6 个上下文块：athena/few_shot/knowledge_base/longform/retrieval/style）、
dialog_prompts（对话提示词）、prompt_optimizer（风格规则）、chapter_target（章节目标）、
json_utils（JSON 解析工具）

## E. athena 检索/实体辅助
athena_longform（长形式分析→世界提案）、athena_entity_resolver（实体解析，依赖 world 表）、
athena_chapter_candidates（章节候选）、athena_setup_terms（设定术语）、
l1_extractor/l2_extractor（分层提取器）

## F. 对话/任务/杂项
chat_commands、dialog_agent_routes、event_bus、error_handler、ui_hints、text_stats、
local_diagnostics、topology_builder、writing_scheduler、background_analyzer

## G. 模型层（16 个，legacy/models/）
dialog、dialog_message、writing_state、version、topology、storyline、background_task、
extracted_fact、genre_profile、pending_action、project_profile_version、ai_model_call_trace、
consistency_check、few_shot_example、chapter_revision（含 RevisionAnnotation/Correction）、
writing_agent

## H. 记忆辅助（legacy/domain/）
narrative_plan_window（情节线窗口）、longform_context_summary（上下文摘要）、
memory_provenance_contract（记忆来源契约）

## I. 脚本（legacy/scripts/ + scripts/ 遗留）
cleanup_athena_setup_entities、longform_scale_smoke、l3_verify、l3_quick_verify、
l4_dogfood、l4_prepare_project、l4_quick_dogfood、m5_test、m5_30ch_test、m5_full_test、
seed_athena_e2e、backfill_entity_states
