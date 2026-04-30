export type AthenaPrimarySection = 'overview' | 'catalog' | 'narrative' | 'truth' | 'review'
export type AthenaCatalogView = 'nodes' | 'graph' | 'rules'
export type AthenaNarrativeView = 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'
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

export interface AthenaNavItem {
  section: AthenaPrimarySection
  label: string
  defaultView: AthenaSubview
}

export interface AthenaRouteIntent {
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
  tool: string | null
  panel: string | null
}

export interface AthenaRouteState extends AthenaRouteIntent {
  isLegacy: boolean
}

type QueryLike = Record<string, string | string[] | null | undefined>

const catalogViews = ['nodes', 'graph', 'rules'] as const
const narrativeViews = ['timeline', 'storyline', 'chapters', 'foreshadowing'] as const
const truthViews = ['facts', 'projection', 'knowledge', 'disclosure'] as const
const reviewViews = ['proposals', 'impact', 'conflicts', 'history'] as const
const nodeTypes = ['all', 'characters', 'locations', 'factions', 'items', 'resources', 'concepts'] as const

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

export function resolveAthenaRoute(rawSection: string | undefined, query: QueryLike): AthenaRouteState {
  const tool = firstQueryValue(query.tool)
  const panel = firstQueryValue(query.panel)
  const legacyRoute = rawSection ? legacyRoutes[rawSection] : undefined

  if (legacyRoute) {
    const section = legacyRoute.section
    const view = resolveCanonicalView(section, legacyRoute.view)

    return {
      section,
      view,
      nodeType: resolveScopedNodeType(section, view, legacyRoute.nodeType ?? null),
      tool: legacyRoute.tool ?? tool,
      panel: legacyRoute.panel ?? panel,
      isLegacy: true,
    }
  }

  const section = isPrimarySection(rawSection) ? rawSection : 'overview'
  const view = resolveCanonicalView(section, firstQueryValue(query.view))

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
    const singleValue = firstQueryValue(value)
    if (singleValue) comparable[key] = singleValue
  }
  return comparable
}

function queriesEqual(left: Record<string, string>, right: Record<string, string>) {
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

  if (state.section !== 'overview') {
    query.view = view
  }
  if (state.section === 'catalog' && view === 'nodes' && nodeType !== 'all') {
    query.type = nodeType
  }
  if (state.tool) {
    query.tool = state.tool
  }
  if (state.panel) {
    query.panel = state.panel
  }

  return {
    path: `/projects/${projectId}/athena/${state.section}`,
    query,
  }
}
