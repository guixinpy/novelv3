import type { Ref } from 'vue'
import { api } from '../../api/client'
import type {
  PaginatedProposalBundles,
  ProposalBundleDetail,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
} from '../../api/types'
import { toErrorMessage } from './errors'

interface ProposalContext {
  ensureProject: (projectId: string) => void
  cacheKey: (projectId: string, resource: string) => string
  requestCache: {
    invalidate: (key: string) => void
  }
  error: Ref<string | null>
  proposals: Ref<PaginatedProposalBundles | null>
  proposalDetails: Ref<Record<string, ProposalBundleDetail>>
  proposalBusy: Ref<Record<string, boolean>>
}

export function createAthenaProposalActions(ctx: ProposalContext) {
  async function loadProposals(
    projectId: string,
    params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string },
  ) {
    ctx.ensureProject(projectId)
    try {
      ctx.proposals.value = await api.getAthenaEvolutionProposals(projectId, params)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    }
  }

  async function loadProposalDetail(projectId: string, bundleId: string) {
    ctx.ensureProject(projectId)
    try {
      ctx.proposalDetails.value[bundleId] = await api.getAthenaProposalDetail(projectId, bundleId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    }
  }

  async function reviewProposalItem(projectId: string, bundleId: string, itemId: string, payload: ProposalReviewRequest) {
    ctx.ensureProject(projectId)
    ctx.proposalBusy.value[itemId] = true
    try {
      await api.reviewAthenaProposalItem(projectId, itemId, payload)
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, 'proposals'))
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      ctx.proposalBusy.value[itemId] = false
    }
  }

  async function splitProposalItem(projectId: string, bundleId: string, itemId: string, reason: string) {
    ctx.ensureProject(projectId)
    ctx.proposalBusy.value[itemId] = true
    const payload: ProposalSplitRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
      item_ids: [itemId],
    }
    try {
      ctx.proposalDetails.value[bundleId] = await api.splitAthenaProposalBundle(projectId, bundleId, payload)
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, 'proposals'))
      await loadProposals(projectId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      ctx.proposalBusy.value[itemId] = false
    }
  }

  async function rollbackProposalReview(projectId: string, bundleId: string, itemId: string, reviewId: string, reason: string) {
    ctx.ensureProject(projectId)
    ctx.proposalBusy.value[itemId] = true
    const payload: ProposalRollbackRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
    }
    try {
      await api.rollbackAthenaProposalReview(projectId, reviewId, payload)
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, 'proposals'))
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      ctx.proposalBusy.value[itemId] = false
    }
  }

  async function batchApproveLowRiskItems(projectId: string, bundleId: string) {
    ctx.ensureProject(projectId)
    if (!ctx.proposalDetails.value[bundleId]) {
      await loadProposalDetail(projectId, bundleId)
    }
    const detail = ctx.proposalDetails.value[bundleId]
    if (!detail) return
    const conflictedItemIds = new Set(detail.conflicts.map((conflict) => conflict.item_id))
    const items = detail.items.filter((item) =>
      ['pending', 'needs_edit'].includes(item.item_status) && !conflictedItemIds.has(item.id),
    )
    try {
      for (const item of items) {
        ctx.proposalBusy.value[item.id] = true
        await api.reviewAthenaProposalItem(projectId, item.id, {
          reviewer_ref: 'athena.batch',
          action: 'approve',
          reason: '批量通过低风险候选',
          evidence_refs: [],
          edited_fields: {},
        })
        ctx.proposalBusy.value[item.id] = false
      }
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, 'proposals'))
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      for (const item of items) {
        ctx.proposalBusy.value[item.id] = false
      }
    }
  }

  return {
    loadProposals,
    loadProposalDetail,
    reviewProposalItem,
    splitProposalItem,
    rollbackProposalReview,
    batchApproveLowRiskItems,
  }
}
