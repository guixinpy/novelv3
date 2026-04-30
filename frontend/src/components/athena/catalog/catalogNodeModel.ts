import type { AthenaNodeTypeFilter } from '../../../views/athenaNavigation'
import type { AthenaOntology, ProposalItem, WorldProjection, WorldProjectionPresence } from '../../../api/types'

export type CatalogNodeType = 'characters' | 'locations' | 'factions' | 'items' | 'resources' | 'concepts'

export interface CatalogNode {
  ref: string
  id: string
  type: CatalogNodeType
  label: string
  aliases: string[]
  raw: Record<string, unknown>
  facts: Record<string, unknown>
  presence: WorldProjectionPresence | null
  relationCount: number
  factCount: number
  pendingCount: number
}

export interface CatalogRelation {
  id?: string
  source_ref?: string
  target_ref?: string
  source_entity_ref?: string
  target_entity_ref?: string
  relation_type?: string
  [key: string]: unknown
}

export interface BuildCatalogNodesInput {
  ontology: AthenaOntology | null
  projection: WorldProjection | null
  pendingProposalItems: ProposalItem[]
}

const entityTypeMap: Record<string, CatalogNodeType | undefined> = {
  characters: 'characters',
  locations: 'locations',
  factions: 'factions',
  artifacts: 'items',
  items: 'items',
  resources: 'resources',
  concepts: 'concepts',
}

const refKeys = [
  'canonical_id',
  'ref',
  'entity_ref',
  'id',
  'character_id',
  'location_id',
  'faction_id',
  'artifact_id',
  'resource_id',
  'canonical_id',
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function resolveRef(record: Record<string, unknown>): string | null {
  for (const key of refKeys) {
    const value = readString(record, key)
    if (value) return value
  }

  return null
}

function resolveLabel(record: Record<string, unknown>, ref: string): string {
  return readString(record, 'name') ?? readString(record, 'primary_alias') ?? ref
}

function resolveAliases(record: Record<string, unknown>): string[] {
  const aliases = record.aliases
  if (!Array.isArray(aliases)) return []

  return aliases.map((alias) => String(alias))
}

function collectProjectionRelations(projection: WorldProjection | null): unknown[] {
  const relations = projection?.relations
  if (Array.isArray(relations)) return relations
  if (!isRecord(relations)) return []

  return Object.values(relations)
}

function collectOntologyRelations(ontology: AthenaOntology): unknown[] {
  return Array.isArray(ontology.relations) ? ontology.relations : []
}

function dedupeRelations(relations: CatalogRelation[]): CatalogRelation[] {
  const seen = new Set<string>()
  const deduped: CatalogRelation[] = []

  relations.forEach((relation) => {
    const keys = [
      typeof relation.id === 'string' && relation.id.length > 0 ? `id:${relation.id}` : null,
      `edge:${relation.source_ref ?? ''}|${relation.target_ref ?? ''}|${relation.relation_type ?? ''}`,
    ].filter((key): key is string => key !== null)
    if (keys.some((key) => seen.has(key))) return

    keys.forEach((key) => seen.add(key))
    deduped.push(relation)
  })

  return deduped
}

function countRelations(ref: string, relations: CatalogRelation[]): number {
  return relations.filter((relation) => relation.source_ref === ref || relation.target_ref === ref).length
}

function countPendingItems(ref: string, pendingProposalItems: ProposalItem[]): number {
  return pendingProposalItems.filter((item) => item.item_status === 'pending' && item.subject_ref === ref).length
}

function projectionRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function valueToSearchText(value: unknown, seen = new WeakSet<object>()): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  if (typeof value === 'symbol') return value.description ?? ''
  if (typeof value === 'function') return ''
  if (Array.isArray(value)) return value.map((item) => valueToSearchText(item, seen)).join(' ')
  if (typeof value === 'object') {
    if (seen.has(value)) return ''

    seen.add(value)
    return Object.values(value).map((item) => valueToSearchText(item, seen)).join(' ')
  }

  return ''
}

function searchableText(node: CatalogNode): string {
  return [
    node.ref,
    node.label,
    ...node.aliases,
    valueToSearchText(node.raw),
    valueToSearchText(node.facts),
  ].join(' ')
}

export function normalizeRelations(relations: unknown[]): CatalogRelation[] {
  return relations.filter(isRecord).map((relation) => {
    const normalized: CatalogRelation = { ...relation }
    const sourceRef = typeof normalized.source_ref === 'string' ? normalized.source_ref : normalized.source_entity_ref
    const targetRef = typeof normalized.target_ref === 'string' ? normalized.target_ref : normalized.target_entity_ref

    if (typeof sourceRef === 'string') normalized.source_ref = sourceRef
    if (typeof targetRef === 'string') normalized.target_ref = targetRef

    return normalized
  })
}

export function buildCatalogNodes(input: BuildCatalogNodesInput): CatalogNode[] {
  const { ontology, projection, pendingProposalItems } = input
  if (!ontology) return []

  const relations = dedupeRelations(normalizeRelations([
    ...collectOntologyRelations(ontology),
    ...collectProjectionRelations(projection),
  ]))
  const ontologyEntities = projectionRecord(ontology.entities)
  const projectionEntities = projectionRecord(projection?.entities)
  const projectionFacts = projectionRecord(projection?.facts)
  const projectionPresence = projectionRecord(projection?.presence)
  const nodes: CatalogNode[] = []

  Object.entries(ontologyEntities).forEach(([entityKey, entities]) => {
    const type = entityTypeMap[entityKey]
    if (!type) return
    if (!Array.isArray(entities)) return

    entities.forEach((entity) => {
      if (!isRecord(entity)) return

      const ontologyItem = entity
      const ref = resolveRef(ontologyItem)
      if (!ref) return

      const projectionEntity = projectionEntities[ref]
      const projectionAttributes = isRecord(projectionEntity) ? projectionRecord(projectionEntity.attributes) : {}
      const facts = projectionRecord(projectionFacts[ref])
      const presence = projectionPresence[ref]

      nodes.push({
        ref,
        id: readString(ontologyItem, 'id') ?? ref,
        type,
        label: resolveLabel(ontologyItem, ref),
        aliases: resolveAliases(ontologyItem),
        raw: { ...projectionAttributes, ...ontologyItem },
        facts,
        presence: isRecord(presence) ? presence : null,
        relationCount: countRelations(ref, relations),
        factCount: Object.keys(facts).length,
        pendingCount: countPendingItems(ref, pendingProposalItems),
      })
    })
  })

  return nodes.sort((a, b) => a.label.localeCompare(b.label, 'zh-Hans-CN') || a.ref.localeCompare(b.ref))
}

export function filterCatalogNodes(
  nodes: CatalogNode[],
  filters: { nodeType: AthenaNodeTypeFilter; search: string },
): CatalogNode[] {
  const search = filters.search.trim().toLocaleLowerCase()

  return nodes.filter((node) => {
    if (filters.nodeType !== 'all' && node.type !== filters.nodeType) return false
    if (!search) return true

    return searchableText(node).toLocaleLowerCase().includes(search)
  })
}
