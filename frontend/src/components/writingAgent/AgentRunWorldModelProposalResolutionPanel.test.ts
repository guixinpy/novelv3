// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWorldModelProposalResolutionPanel from './AgentRunWorldModelProposalResolutionPanel.vue'

describe('AgentRunWorldModelProposalResolutionPanel', () => {
  it('renders world model proposal resolution plan projection without internal ids', () => {
    const wrapper = mount(AgentRunWorldModelProposalResolutionPanel, {
      props: {
        output: {
          status: 'blocked',
          project_id: 'project-secret-id',
          profile_version: 'profile-secret-version',
          total_items: 3,
          returned_items: 3,
          offset: 2,
          limit: 7,
          has_more: false,
          risk_counts: { high: 1, medium: 0, low: 2 },
          review_mode_counts: { individual: 1, batch: 2 },
          high_priority_step_count: 1,
          batch_step_count: 1,
          requires_human_confirmation: true,
          can_auto_apply: false,
          should_generate_next_chapter: false,
          recommended_actions: [
            'pause_generation_until_proposals_resolved',
            'resolve_individual_proposals_first',
            'resolve_batch_proposals_after_individuals',
          ],
          recommended_next_tools: ['review_world_model_proposals'],
          plan_only: true,
          report_only: true,
          resolution_steps: [
            {
              step_index: 1,
              action_type: 'review_individual',
              recommended_resolution: 'manual_individual_review',
              requires_human_confirmation: true,
              risk_level: 'high',
              review_mode: 'individual',
              cluster_id: 'cluster-secret-id',
              candidate_count: 1,
              item_ids: ['item-secret-id'],
              bundle_ids: ['bundle-secret-id'],
              subject_refs: ['char.hero'],
              predicate: 'status',
              chapter_range: { start: 1, end: 1 },
              reason: '高风险状态事实需先逐项审阅',
              allowed_actions: ['approve', 'reject', 'mark_uncertain'],
            },
            {
              step_index: 2,
              action_type: 'review_batch',
              recommended_resolution: 'batch_review',
              requires_human_confirmation: true,
              risk_level: 'low',
              review_mode: 'batch',
              cluster_id: 'cluster-secret-id-2',
              candidate_count: 2,
              item_ids: ['item-secret-id-2', 'item-secret-id-3'],
              bundle_ids: ['bundle-secret-id-2'],
              subject_refs: ['char.partner'],
              predicate: 'mentioned_in_chapter',
              chapter_range: { start: 2, end: 3 },
              reason: '低风险出场事实可在高风险后批量审阅',
              allowed_actions: ['approve', 'approve_with_edits', 'reject'],
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('世界模型提案解决计划')
    expect(text).toContain('已阻塞')
    expect(text).toContain('需要人工确认')
    expect(text).toContain('不可自动应用')
    expect(text).toContain('不可继续生成')
    expect(text).toContain('返回 3 / 3')
    expect(text).toContain('高优先级步骤 1')
    expect(text).toContain('批量步骤 1')
    expect(text).toContain('高风险 1')
    expect(text).toContain('低风险 2')
    expect(text).toContain('逐项审阅 1')
    expect(text).toContain('批量审阅 2')
    expect(text).toContain('pause_generation_until_proposals_resolved')
    expect(text).toContain('resolve_individual_proposals_first')
    expect(text).toContain('resolve_batch_proposals_after_individuals')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('#1 char.hero · status')
    expect(text).toContain('逐项审阅 · 手动逐项审阅 · 高风险 · 1 个候选 · 第1章')
    expect(text).toContain('高风险状态事实需先逐项审阅')
    expect(text).toContain('#2 char.partner · mentioned_in_chapter')
    expect(text).toContain('批量审阅 · 批量审阅 · 低风险 · 2 个候选 · 第2-3章')
    expect(text).toContain('低风险出场事实可在高风险后批量审阅')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('profile-secret-version')
    expect(text).not.toContain('cluster-secret-id')
    expect(text).not.toContain('item-secret-id')
    expect(text).not.toContain('bundle-secret-id')
    expect(text).not.toContain('profile_version')
    expect(text).not.toContain('item_ids')
    expect(text).not.toContain('bundle_ids')
    expect(text).not.toContain('allowed_actions')
    expect(text).not.toContain('plan_only')
    expect(text).not.toContain('report_only')
  })
})
