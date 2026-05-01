export type AthenaPrimarySection = 'overview' | 'catalog' | 'narrative' | 'truth' | 'review'
export type AthenaCatalogView = 'nodes' | 'graph' | 'rules'
export type AthenaNarrativeView = 'timeline' | 'storyline' | 'chapters' | 'foreshadowing' | 'graph'
export type AthenaTruthView = 'facts' | 'projection' | 'knowledge' | 'disclosure'
export type AthenaReviewView = 'proposals' | 'impact' | 'conflicts' | 'history'
export type AthenaOverviewView = 'dashboard'
export type AthenaSubview =
  | AthenaOverviewView
  | AthenaCatalogView
  | AthenaNarrativeView
  | AthenaTruthView
  | AthenaReviewView

export type AthenaNodeTypeFilter =
  | 'all'
  | 'characters'
  | 'locations'
  | 'factions'
  | 'items'
  | 'resources'
  | 'concepts'

export type AthenaTool = 'retrieval'
export type AthenaPanel = 'optimization' | 'chat'

export interface AthenaNavItem {
  section: AthenaPrimarySection
  label: string
  defaultView: AthenaSubview
}

export interface AthenaRouteIntent {
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
  tool: AthenaTool | null
  panel: AthenaPanel | null
}

export interface AthenaRouteState extends AthenaRouteIntent {
  isLegacy: boolean
}

type QueryLike = Record<string, string | string[] | null | undefined>

const catalogViews = ['nodes', 'graph', 'rules'] as const
const narrativeViews = ['timeline', 'storyline', 'chapters', 'foreshadowing', 'graph'] as const
const truthViews = ['facts', 'projection', 'knowledge', 'disclosure'] as const
const reviewViews = ['proposals', 'impact', 'conflicts', 'history'] as const
const nodeTypes = ['all', 'characters', 'locations', 'factions', 'items', 'resources', 'concepts'] as const
const tools = ['retrieval'] as const
const panels = ['optimization', 'chat'] as const

export const athenaPrimaryNav: AthenaNavItem[] = [
  { section: 'overview', label: '总览', defaultView: 'dashboard' },
  { section: 'catalog', label: '设定库', defaultView: 'nodes' },
  { section: 'narrative', label: '叙事脉络', defaultView: 'timeline' },
  { section: 'truth', label: '真相认知', defaultView: 'projection' },
  { section: 'review', label: '待审变更', defaultView: 'proposals' },
]

const canonicalDefaults: Record<AthenaPrimarySection, AthenaSubview> = {
  overview: 'dashboard',
  catalog: 'nodes',
  narrative: 'timeline',
  truth: 'projection',
  review: 'proposals',
}

const legacyRoutes: Record<string, Partial<AthenaRouteState> & Pick<AthenaRouteState, 'section' | 'view'>> = {
  characters: { section: 'catalog', view: 'nodes', nodeType: 'characters' },
  locations: { section: 'catalog', view: 'nodes', nodeType: 'locations' },
  factions: { section: 'catalog', view: 'nodes', nodeType: 'factions' },
  items: { section: 'catalog', view: 'nodes', nodeType: 'items' },
  relations: { section: 'catalog', view: 'graph' },
  rules: { section: 'catalog', view: 'rules' },
  timeline: { section: 'narrative', view: 'timeline' },
  storyline: { section: 'narrative', view: 'storyline' },
  outline: { section: 'narrative', view: 'chapters' },
  projection: { section: 'truth', view: 'projection' },
  knowledge: { section: 'truth', view: 'knowledge' },
  proposals: { section: 'review', view: 'proposals' },
  consistency: { section: 'review', view: 'conflicts' },
  retrieval: { section: 'catalog', view: 'nodes', tool: 'retrieval' },
  optimization: { section: 'overview', view: 'dashboard', panel: 'optimization' },
  chat: { section: 'overview', view: 'dashboard', panel: 'chat' },
}

function firstQueryValue(value: string | string[] | null | undefined) {
  const singleValue = Array.isArray(value) ? value[0] : value
  return singleValue || null
}

function isPrimarySection(value: string | undefined): value is AthenaPrimarySection {
  return value === 'overview' || value === 'catalog' || value === 'narrative' || value === 'truth' || value === 'review'
}

function isOneOf<T extends string>(value: string | null, allowed: readonly T[]): value is T {
  return value !== null && allowed.includes(value as T)
}

function resolveCanonicalView(section: AthenaPrimarySection, queryView: string | null): AthenaSubview {
  if (section === 'overview') return 'dashboard'
  if (section === 'catalog') return isOneOf(queryView, catalogViews) ? queryView : canonicalDefaults.catalog
  if (section === 'narrative') return isOneOf(queryView, narrativeViews) ? queryView : canonicalDefaults.narrative
  if (section === 'truth') return isOneOf(queryView, truthViews) ? queryView : canonicalDefaults.truth
  return isOneOf(queryView, reviewViews) ? queryView : canonicalDefaults.review
}

function resolveNodeType(queryType: string | null): AthenaNodeTypeFilter {
  return isOneOf(queryType, nodeTypes) ? queryType : 'all'
}

function resolveScopedNodeType(
  section: AthenaPrimarySection,
  view: AthenaSubview,
  queryType: string | null,
): AthenaNodeTypeFilter {
  if (section !== 'catalog' || view !== 'nodes') return 'all'
  return resolveNodeType(queryType)
}

function resolveScopedTool(section: AthenaPrimarySection, view: AthenaSubview, queryTool: string | null): AthenaTool | null {
  if (section !== 'catalog' || view !== 'nodes') return null
  return isOneOf(queryTool, tools) ? queryTool : null
}

function resolveScopedPanel(section: AthenaPrimarySection, view: AthenaSubview, queryPanel: string | null): AthenaPanel | null {
  if (queryPanel === 'chat') return 'chat'
  if (section !== 'overview' || view !== 'dashboard') return null
  return isOneOf(queryPanel, panels) ? queryPanel : null
}

export function resolveAthenaRoute(rawSection: string | undefined, query: QueryLike): AthenaRouteState {
  const legacyRoute = rawSection ? legacyRoutes[rawSection] : undefined

  if (legacyRoute) {
    const section = legacyRoute.section
    const view = resolveCanonicalView(section, legacyRoute.view)
    const tool = resolveScopedTool(section, view, legacyRoute.tool ?? firstQueryValue(query.tool))
    const panel = resolveScopedPanel(section, view, legacyRoute.panel ?? firstQueryValue(query.panel))

    return {
      section,
      view,
      nodeType: resolveScopedNodeType(section, view, legacyRoute.nodeType ?? null),
      tool,
      panel,
      isLegacy: true,
    }
  }

  const section = isPrimarySection(rawSection) ? rawSection : 'overview'
  const view = resolveCanonicalView(section, firstQueryValue(query.view))
  const tool = resolveScopedTool(section, view, firstQueryValue(query.tool))
  const panel = resolveScopedPanel(section, view, firstQueryValue(query.panel))

  return {
    section,
    view,
    nodeType: resolveScopedNodeType(section, view, firstQueryValue(query.type)),
    tool,
    panel,
    isLegacy: false,
  }
}

export function defaultAthenaRouteState(section: AthenaPrimarySection = 'overview'): AthenaRouteIntent {
  return {
    section,
    view: canonicalDefaults[section],
    nodeType: 'all',
    tool: null,
    panel: null,
  }
}

function comparableQuery(query: QueryLike) {
  const comparable: Record<string, string> = {}
  for (const [key, value] of Object.entries(query)) {
    if (Array.isArray(value)) {
      if (value.length !== 1 || !value[0]) return null
      comparable[key] = value[0]
      continue
    }
    if (!value) return null
    comparable[key] = value
  }
  return comparable
}

function queriesEqual(left: Record<string, string> | null, right: Record<string, string>) {
  if (!left) return false
  const leftKeys = Object.keys(left)
  const rightKeys = Object.keys(right)
  return leftKeys.length === rightKeys.length && leftKeys.every((key) => left[key] === right[key])
}

export function isCanonicalAthenaRoute(
  projectId: string,
  state: AthenaRouteIntent,
  currentPath: string,
  currentQuery: QueryLike,
) {
  const target = buildAthenaRoute(projectId, state)
  return currentPath === target.path && queriesEqual(comparableQuery(currentQuery), target.query)
}

export function buildAthenaRoute(projectId: string, state: AthenaRouteIntent): { path: string; query: Record<string, string> } {
  const query: Record<string, string> = {}
  const view = resolveCanonicalView(state.section, state.view)
  const nodeType = resolveScopedNodeType(state.section, view, state.nodeType)
  const tool = resolveScopedTool(state.section, view, state.tool)
  const panel = resolveScopedPanel(state.section, view, state.panel)

  if (state.section !== 'overview') {
    query.view = view
  }
  if (state.section === 'catalog' && view === 'nodes' && nodeType !== 'all') {
    query.type = nodeType
  }
  if (tool) {
    query.tool = tool
  }
  if (panel) {
    query.panel = panel
  }

  return {
    path: `/projects/${projectId}/athena/${state.section}`,
    query,
  }
}
