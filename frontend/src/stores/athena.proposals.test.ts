import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaProposalDetail: vi.fn(),
    reviewAthenaProposalItem: vi.fn(),
    getAthenaEvolutionProposals: vi.fn(),
    importAthenaSetup: vi.fn(),
    analyzeAthenaChapter: vi.fn(),
    getAthenaOntology: vi.fn(),
  },
}))

const detail = {
  bundle: {
    id: 'bundle-1',
    project_id: 'project-1',
    project_profile_version_id: 'profile-1',
    profile_version: 1,
    parent_bundle_id: null,
    bundle_status: 'pending',
    title: '第1章世界事实候选',
    summary: '',
    created_by: 'athena.chapter_analyzer',
    created_at: '2026-04-28T00:00:00Z',
    updated_at: '2026-04-28T00:00:00Z',
  },
  items: [
    {
      id: 'item-1',
      bundle_id: 'bundle-1',
      parent_item_id: null,
      item_status: 'pending',
      claim_id: 'claim.1',
      subject_ref: 'char.林舟',
      predicate: 'presence_count',
      object_ref_or_value: { count: 2 },
      claim_layer: 'truth',
      evidence_refs: ['chapter:1'],
      authority_type: 'derived',
      confidence: 0.9,
      contract_version: 'world.contract.v1',
      approved_claim_id: null,
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-28T00:00:00Z',
    },
  ],
  reviews: [],
  impact_snapshots: [],
  conflicts: [],
}

describe('athena proposal workflow store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads proposal detail and batch approves actionable low-risk items', async () => {
    vi.mocked(api.getAthenaProposalDetail).mockResolvedValue(detail)
    vi.mocked(api.reviewAthenaProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'athena.batch',
      reason: '批量通过低风险候选',
      evidence_refs: [],
      edited_fields: {},
      created_truth_claim_id: 'claim.1',
      rollback_to_review_id: null,
      created_at: '2026-04-28T00:00:00Z',
    })
    vi.mocked(api.getAthenaEvolutionProposals).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 })
    const store = useAthenaStore()

    await store.loadProposalDetail('project-1', 'bundle-1')
    await store.batchApproveLowRiskItems('project-1', 'bundle-1')

    expect(store.proposalDetails['bundle-1']?.items[0].subject_ref).toBe('char.林舟')
    expect(api.reviewAthenaProposalItem).toHaveBeenCalledWith('project-1', 'item-1', {
      reviewer_ref: 'athena.batch',
      action: 'approve',
      reason: '批量通过低风险候选',
      evidence_refs: [],
      edited_fields: {},
    })
    expect(api.getAthenaProposalDetail).toHaveBeenCalledTimes(2)
  })

  it('imports setup and refreshes ontology', async () => {
    vi.mocked(api.importAthenaSetup).mockResolvedValue({
      status: 'completed',
      profile_version: 1,
      project_profile_version_id: 'profile-1',
      created: { profile: 1, characters: 2, rules: 1 },
    })
    vi.mocked(api.getAthenaOntology).mockResolvedValue({
      entities: {},
      relations: [],
      rules: [],
      setup_summary: null,
      profile_version: 1,
    })
    const store = useAthenaStore()

    await store.importSetup('project-1')

    expect(api.importAthenaSetup).toHaveBeenCalledWith('project-1')
    expect(api.getAthenaOntology).toHaveBeenCalledWith('project-1')
  })

  it('analyzes a chapter and refreshes proposals', async () => {
    vi.mocked(api.analyzeAthenaChapter).mockResolvedValue({
      status: 'completed',
      chapter_index: 1,
      task_id: null,
      proposal_bundle_id: 'bundle-1',
      created: { proposal_items: 2 },
      skipped: { duplicates: 0 },
    })
    vi.mocked(api.getAthenaEvolutionProposals).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 })
    const store = useAthenaStore()

    await store.analyzeChapter('project-1', 1)

    expect(api.analyzeAthenaChapter).toHaveBeenCalledWith('project-1', 1)
    expect(api.getAthenaEvolutionProposals).toHaveBeenCalledWith('project-1', undefined)
  })
})
