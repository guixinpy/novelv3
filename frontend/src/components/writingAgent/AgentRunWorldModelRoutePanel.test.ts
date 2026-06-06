// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWorldModelRoutePanel from './AgentRunWorldModelRoutePanel.vue'

describe('AgentRunWorldModelRoutePanel', () => {
  it('renders world model route projection without internal ids', () => {
    const wrapper = mount(AgentRunWorldModelRoutePanel, {
      props: {
        output: {
          status: 'completed',
          project_id: 'project-secret-id',
          chapter_index: 2,
          subject_ref: 'char.hero',
          profile: {
            id: 'profile-secret-id',
            version: 3,
            contract_version: 'world.contract.v1',
          },
          route: {
            status: 'blocked',
            reason: 'pending_world_model_proposals',
            can_use_world_model: true,
            pending_proposal_count: 2,
          },
          fact_summary: {
            total_confirmed_facts: 3,
            returned_facts: 1,
            limit: 5,
          },
          facts: [
            {
              id: 'fact-secret-id',
              claim_id: 'claim.secret.hero.identity',
              chapter_index: 1,
              subject_ref: 'char.hero',
              predicate: 'identity',
              object_ref_or_value: '灯塔区调查员',
              claim_layer: 'truth',
              claim_status: 'confirmed',
              confidence: 0.95,
              evidence_refs: ['chapter:1', 'world_profile:secret'],
            },
          ],
          proposal_pressure: {
            status: 'blocked',
            total_items: 2,
            risk_counts: { high: 1, medium: 1, low: 0 },
            review_mode_counts: { individual: 1, batch: 1 },
            clusters: [
              {
                cluster_id: 'cluster-secret-id',
                risk_level: 'high',
                review_mode: 'individual',
                candidate_count: 2,
                item_ids: ['item-secret-id'],
                bundle_ids: ['bundle-secret-id'],
                subject_refs: ['char.hero'],
                predicate: 'identity',
                chapter_range: { start: 1, end: 2 },
                reason: '同一角色身份存在待审冲突',
              },
            ],
          },
          recommended_actions: ['review_world_model_proposals'],
          diagnostics: [
            {
              code: 'pending_world_model_proposals',
              severity: 'warning',
              message: '世界模型存在待处理事项，Agent 应先处理后再继续生成或修订。',
              pending_proposal_count: 2,
            },
          ],
          trace: {
            source: 'inspect_agent_world_model_route',
            version: 'phase74.agent_world_model_route.v1',
            mutability: 'read',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('世界模型路由')
    expect(text).toContain('已阻塞')
    expect(text).toContain('可用于生成')
    expect(text).toContain('第2章')
    expect(text).toContain('char.hero')
    expect(text).toContain('确认事实 1 / 3')
    expect(text).toContain('待审提案 2')
    expect(text).toContain('高风险 1')
    expect(text).toContain('中风险 1')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('identity')
    expect(text).toContain('灯塔区调查员')
    expect(text).toContain('置信 0.95')
    expect(text).toContain('同一角色身份存在待审冲突')
    expect(text).toContain('世界模型存在待处理事项')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('profile-secret-id')
    expect(text).not.toContain('fact-secret-id')
    expect(text).not.toContain('claim.secret.hero.identity')
    expect(text).not.toContain('chapter:1')
    expect(text).not.toContain('world_profile:secret')
    expect(text).not.toContain('cluster-secret-id')
    expect(text).not.toContain('item-secret-id')
    expect(text).not.toContain('bundle-secret-id')
    expect(text).not.toContain('phase74.agent_world_model_route.v1')
    expect(text).not.toContain('source')
  })
})
