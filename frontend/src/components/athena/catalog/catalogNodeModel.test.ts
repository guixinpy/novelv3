import { describe, expect, it } from 'vitest'
import { buildCatalogNodes, filterCatalogNodes, normalizeRelations } from './catalogNodeModel'
import type { AthenaOntology, ProposalItem, WorldProjection } from '../../../api/types'

const ontology: AthenaOntology = {
  entities: {
    characters: [{ id: 'char.linche', name: '林澈', role_type: 'protagonist', core_drives: ['查清旧案'] } as any],
    locations: [{ id: 'loc.lighthouse', name: '旧灯塔', location_type: 'landmark', hazards: ['潮汐异常'] } as any],
    factions: [{ id: 'fac.tidegate', name: '潮汐门', faction_type: 'secret_order', hidden_agenda: '控制潮痕' } as any],
    artifacts: [{ id: 'art.lamp', name: '旧灯牌', artifact_type: 'token', function_summary: '打开旧门' } as any],
  },
  relations: [
    { id: 'rel-1', source_ref: 'char.linche', target_ref: 'loc.lighthouse', relation_type: 'guards' },
  ],
  rules: [{ id: 'rule-1', rule_id: 'rule.tide', description: '潮汐会吞没记忆' }],
  setup_summary: null,
  profile_version: 1,
}

const projection: WorldProjection = {
  view_type: 'current_truth',
  entities: {
    'char.linche': { entity_type: 'character', attributes: { public_persona: '守夜人' } },
  },
  relations: {},
  presence: { 'char.linche': { location_ref: 'loc.lighthouse', presence_status: 'active' } },
  occurred_events: {},
  event_links: {},
  facts: {
    'char.linche': { hidden_truth: '父亲失踪与潮汐门有关' },
  },
}

describe('catalogNodeModel', () => {
  it('builds catalog nodes with type, facts, relations, and presence', () => {
    const nodes = buildCatalogNodes({ ontology, projection, pendingProposalItems: [] })
    const character = nodes.find((node) => node.ref === 'char.linche')

    expect(character).toMatchObject({
      ref: 'char.linche',
      type: 'characters',
      label: '林澈',
      relationCount: 1,
      factCount: 1,
      pendingCount: 0,
    })
    expect(character?.presence?.location_ref).toBe('loc.lighthouse')
  })

  it('filters by node type and search text', () => {
    const nodes = buildCatalogNodes({ ontology, projection, pendingProposalItems: [] })

    expect(filterCatalogNodes(nodes, { nodeType: 'characters', search: '' }).map((node) => node.label)).toEqual(['林澈'])
    expect(filterCatalogNodes(nodes, { nodeType: 'all', search: '灯塔' }).map((node) => node.label)).toEqual(['旧灯塔'])
  })

  it('normalizes relation endpoint fields while preserving originals', () => {
    expect(normalizeRelations([
      { id: 'rel-2', source_entity_ref: 'char.linche', target_entity_ref: 'fac.tidegate', relation_type: 'knows' },
    ])).toEqual([
      {
        id: 'rel-2',
        source_entity_ref: 'char.linche',
        target_entity_ref: 'fac.tidegate',
        source_ref: 'char.linche',
        target_ref: 'fac.tidegate',
        relation_type: 'knows',
      },
    ])
  })

  it('counts pending proposal items and keeps ontology fields over projection attributes', () => {
    const pendingProposalItems = [
      { id: 'item-1', item_status: 'pending', subject_ref: 'char.linche' },
      { id: 'item-2', item_status: 'approved', subject_ref: 'char.linche' },
    ] as ProposalItem[]

    const nodes = buildCatalogNodes({
      ontology,
      projection: {
        ...projection,
        entities: {
          'char.linche': { entity_type: 'character', attributes: { name: '投影名', public_persona: '守夜人' } },
        },
      },
      pendingProposalItems,
    })
    const character = nodes.find((node) => node.ref === 'char.linche')

    expect(character?.pendingCount).toBe(1)
    expect(character?.raw.name).toBe('林澈')
    expect(filterCatalogNodes(nodes, { nodeType: 'all', search: '父亲失踪' }).map((node) => node.ref)).toEqual(['char.linche'])
  })
})
