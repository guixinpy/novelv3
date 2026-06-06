// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWorldModelProposalReviewPanel from './AgentRunWorldModelProposalReviewPanel.vue'

describe('AgentRunWorldModelProposalReviewPanel', () => {
  it('renders world model proposal review projection without internal ids', () => {
    const wrapper = mount(AgentRunWorldModelProposalReviewPanel, {
      props: {
        output: {
          status: 'blocked',
          project_id: 'project-secret-id',
          profile_version: 'profile-secret-version',
          total_items: 3,
          returned_items: 2,
          offset: 0,
          limit: 20,
          has_more: true,
          risk_counts: { high: 1, medium: 1, low: 1 },
          review_mode_counts: { individual: 1, batch: 2 },
          clusters: [
            {
              cluster_id: 'cluster-secret-id',
              risk_level: 'high',
              review_mode: 'individual',
              candidate_count: 1,
              item_ids: ['item-secret-id'],
              bundle_ids: ['bundle-secret-id'],
              subject_refs: ['char.hero'],
              predicate: 'identity',
              chapter_range: { start: 1, end: 1 },
              reason: '主角身份存在待审冲突',
            },
            {
              cluster_id: 'cluster-secret-id-2',
              risk_level: 'low',
              review_mode: 'batch',
              candidate_count: 2,
              item_ids: ['item-secret-id-2', 'item-secret-id-3'],
              bundle_ids: ['bundle-secret-id-2'],
              subject_refs: ['char.partner'],
              predicate: 'mentioned_in_chapter',
              chapter_range: { start: 2, end: 3 },
              reason: '低风险出场事实可批量审阅',
            },
          ],
          recommended_actions: [
            'pause_generation_until_proposals_resolved',
            'review_high_risk_proposals',
            'batch_review_low_risk_proposals',
          ],
          should_generate_next_chapter: false,
          report_only: true,
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('世界模型提案队列')
    expect(text).toContain('已阻塞')
    expect(text).toContain('不可继续生成')
    expect(text).toContain('返回 2 / 3')
    expect(text).toContain('待审 3')
    expect(text).toContain('有更多')
    expect(text).toContain('高风险 1')
    expect(text).toContain('中风险 1')
    expect(text).toContain('低风险 1')
    expect(text).toContain('逐项审阅 1')
    expect(text).toContain('批量审阅 2')
    expect(text).toContain('pause_generation_until_proposals_resolved')
    expect(text).toContain('review_high_risk_proposals')
    expect(text).toContain('batch_review_low_risk_proposals')
    expect(text).toContain('char.hero')
    expect(text).toContain('identity')
    expect(text).toContain('高风险 · 逐项审阅 · 1 个候选 · 第1章')
    expect(text).toContain('主角身份存在待审冲突')
    expect(text).toContain('char.partner')
    expect(text).toContain('mentioned_in_chapter')
    expect(text).toContain('低风险 · 批量审阅 · 2 个候选 · 第2-3章')
    expect(text).toContain('低风险出场事实可批量审阅')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('profile-secret-version')
    expect(text).not.toContain('cluster-secret-id')
    expect(text).not.toContain('item-secret-id')
    expect(text).not.toContain('bundle-secret-id')
    expect(text).not.toContain('profile_version')
    expect(text).not.toContain('item_ids')
    expect(text).not.toContain('bundle_ids')
    expect(text).not.toContain('report_only')
  })
})
