<script setup lang="ts">
import { computed } from 'vue'
import type { WorldFactClaim, WorldProjection } from '../../api/types'

type TruthLedgerView = 'facts' | 'disclosure'
interface TruthRow {
  id: string
  subjectRef: string
  predicate: string
  displayValue: string
  claimLayer: string
  claimStatus: string
  perspectiveRef: string
  disclosedToRefs: string[]
  authorityType: string
  confidence: string
  evidenceRefs: string[]
  chapterIndex: number | null
  sourceEventRef: string
  notes: string
  hasClaimMetadata: boolean
}

const props = defineProps<{
  projection: WorldProjection | null
  factClaims: WorldFactClaim[]
  view: TruthLedgerView
}>()

const factRows = computed<TruthRow[]>(() => {
  if (props.factClaims.length) {
    return props.factClaims.map((claim) => ({
      id: claim.id,
      subjectRef: claim.subject_ref,
      predicate: claim.predicate,
      displayValue: formatValue(claim.object_ref_or_value),
      claimLayer: claim.claim_layer,
      claimStatus: claim.claim_status,
      perspectiveRef: claim.perspective_ref || '',
      disclosedToRefs: claim.disclosed_to_refs || [],
      authorityType: claim.authority_type,
      confidence: formatValue(claim.confidence),
      evidenceRefs: claim.evidence_refs || [],
      chapterIndex: claim.chapter_index ?? null,
      sourceEventRef: claim.source_event_ref || '',
      notes: claim.notes,
      hasClaimMetadata: true,
    }))
  }

  const facts = props.projection?.facts || {}
  return Object.entries(facts).flatMap(([subjectRef, entries]) =>
    Object.entries(entries || {}).map(([predicate, value]) => {
      return {
        id: `${subjectRef}:${predicate}`,
        subjectRef,
        predicate,
        displayValue: formatValue(value),
        claimLayer: 'truth',
        claimStatus: 'projection',
        perspectiveRef: '',
        disclosedToRefs: [],
        authorityType: '',
        confidence: '',
        evidenceRefs: [],
        chapterIndex: null,
        sourceEventRef: '',
        notes: '',
        hasClaimMetadata: false,
      }
    }),
  )
})

const disclosureRows = computed(() =>
  factRows.value.map((row) => ({
    ...row,
    audience: row.disclosedToRefs.length ? row.disclosedToRefs.join(' / ') : '未标注披露对象',
  })),
)

const metrics = computed(() => [
  { label: '事实主体', value: new Set(factRows.value.map((row) => row.subjectRef)).size },
  { label: '事实条目', value: factRows.value.length },
  { label: '披露标记', value: factRows.value.filter((row) => row.disclosedToRefs.length).length },
])

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  if (Array.isArray(value)) return value.map(formatValue).join(' / ')
  return formatObject(value)
}

function formatObject(value: unknown): string {
  try {
    return JSON.stringify(value, (_key, entry) => typeof entry === 'bigint' ? String(entry) : entry)
  } catch (_error) {
    return String(value)
  }
}
</script>

<template>
  <section class="truth-ledger">
    <div v-if="!projection" class="truth-ledger__empty">尚未建立正式 world-model 投影</div>
    <template v-else>
      <div class="truth-ledger__metrics">
        <div v-for="metric in metrics" :key="metric.label" class="truth-ledger__metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </div>

      <div v-if="view === 'facts'" class="truth-ledger__list">
        <article v-for="row in factRows" :key="row.id" class="truth-ledger__row">
          <header>
            <span>{{ row.subjectRef }}</span>
            <strong>{{ row.predicate }}</strong>
          </header>
          <p>{{ row.displayValue }}</p>
          <footer>
            <span>{{ row.claimLayer }}</span>
            <span>{{ row.claimStatus }}</span>
            <span v-if="row.chapterIndex !== null">第{{ row.chapterIndex }}章</span>
            <span v-if="row.authorityType">{{ row.authorityType }}</span>
            <span v-if="row.confidence">置信 {{ row.confidence }}</span>
            <span v-if="row.evidenceRefs.length">证据 {{ row.evidenceRefs.join(' / ') }}</span>
          </footer>
        </article>
        <div v-if="factRows.length === 0" class="truth-ledger__empty">暂无确认事实</div>
      </div>

      <div v-else class="truth-ledger__list">
        <article v-for="row in disclosureRows" :key="row.id" class="truth-ledger__row truth-ledger__row--matrix">
          <header>
            <span>{{ row.subjectRef }}</span>
            <strong>{{ row.predicate }}</strong>
          </header>
          <dl>
            <dt>视角</dt>
            <dd>{{ row.perspectiveRef || '全知/未标注' }}</dd>
            <dt>披露给</dt>
            <dd>{{ row.audience }}</dd>
            <dt>内容</dt>
            <dd>{{ row.displayValue }}</dd>
            <template v-if="row.sourceEventRef">
              <dt>来源事件</dt>
              <dd>{{ row.sourceEventRef }}</dd>
            </template>
            <template v-if="row.notes">
              <dt>备注</dt>
              <dd>{{ row.notes }}</dd>
            </template>
            <template v-if="!row.hasClaimMetadata">
              <dt>元数据</dt>
              <dd>当前投影未携带披露元数据</dd>
            </template>
          </dl>
        </article>
        <div v-if="disclosureRows.length === 0" class="truth-ledger__empty">暂无披露记录</div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.truth-ledger {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.truth-ledger__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.truth-ledger__metric {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.truth-ledger__metric span,
.truth-ledger__row header span,
.truth-ledger__row footer span,
.truth-ledger__row dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.truth-ledger__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
}

.truth-ledger__list {
  display: grid;
  gap: var(--space-3);
}

.truth-ledger__row {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}

.truth-ledger__row header {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.truth-ledger__row strong {
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.truth-ledger__row p,
.truth-ledger__row dd {
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.truth-ledger__row footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.truth-ledger__row dl {
  display: grid;
  grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
  gap: var(--space-2);
}

.truth-ledger__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 760px) {
  .truth-ledger__metrics {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
