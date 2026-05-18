export type DialogState = 'IDLE' | 'CHATTING' | 'PENDING_ACTION' | 'RUNNING'
export type ActionStatus = 'idle' | 'pending' | 'running' | 'completed' | 'success' | 'failed' | 'cancelled' | 'revised'
export type ChatMessageType = 'plain' | 'summary' | 'command'
export type WorkspacePanel =
  | 'overview'
  | 'setup'
  | 'storyline'
  | 'outline'
  | 'content'
  | 'topology'
  | 'versions'
  | 'preferences'
export type RefreshTarget =
  | 'project'
  | 'setup'
  | 'storyline'
  | 'outline'
  | 'content'
  | 'topology'
  | 'versions'
  | 'preferences'
  | 'writing_state'
  | 'ontology'
  | 'state'
  | 'projection'
  | 'proposals'

export interface PendingAction {
  id: string
  type: string
  description: string
  params: Record<string, unknown>
  requires_confirmation: boolean
}

export interface ActiveAction {
  type: string
  status: ActionStatus
  target_panel: WorkspacePanel | null
  reason: string
}

export interface UiHint {
  dialog_state: DialogState
  active_action: ActiveAction
}

export interface ProjectDiagnosis {
  missing_items: string[]
  completed_items: string[]
  suggested_next_step: string | null
}

export interface ProjectSummary {
  id: string
  name: string
  description?: string
  genre?: string
  target_chapter_count?: number
  target_word_count?: number
  style?: string
  complexity?: number
  status?: string
  current_phase?: string
  current_word_count?: number
  ai_model?: string
  language?: string
  created_at?: string
  updated_at?: string
}

export interface ChapterSummary {
  id: string
  chapter_index: number
  title: string
  word_count: number
  status: string
}

export interface ChapterListResponse {
  chapters: ChapterSummary[]
  total?: number
  offset?: number
  limit?: number
  has_more?: boolean
  latest_chapter_index?: number | null
}

export interface VersionSummary {
  id: string
  version_number: number
  node_type: string
  node_id: string
  description?: string
  author?: string
  created_at?: string
}

export interface VersionListResponse {
  versions: VersionSummary[]
  total?: number
  offset?: number
  limit?: number
  has_more?: boolean
}

export interface WritingState {
  project_id: string
  current_chapter: number
  status: string
  last_error?: string | null
  task_id?: string | null
}

export interface DialogBootstrap {
  messages: ChatHistoryMessage[]
}

export interface WorkspaceBootstrap {
  project: ProjectSummary
  diagnosis: ProjectDiagnosis
  setup?: SetupData | null
  setup_partial?: boolean
  storyline?: Record<string, unknown> | null
  storyline_partial?: boolean
  outline?: Record<string, unknown> | null
  outline_partial?: boolean
  chapters: ChapterSummary[]
  chapters_total?: number
  chapters_offset?: number
  chapters_limit?: number
  chapters_has_more?: boolean
  chapters_latest_index?: number | null
  versions: VersionSummary[]
  versions_total?: number
  versions_offset?: number
  versions_limit?: number
  versions_has_more?: boolean
  writing_state?: WritingState | null
  dialogs: {
    hermes?: DialogBootstrap
    athena?: DialogBootstrap
    [key: string]: DialogBootstrap | undefined
  }
}

export interface ChatRequest {
  project_id: string
  input_type: 'text' | 'button' | 'command'
  text?: string
  action_type?: string
  params?: Record<string, unknown>
  command_name?: string
  command_args?: string
}

export interface ChatResponse {
  message: string
  pending_action: PendingAction | null
  ui_hint: UiHint | null
  refresh_targets: RefreshTarget[]
  project_diagnosis: ProjectDiagnosis
  message_type?: ChatMessageType | null
  meta?: Record<string, unknown> | null
  trace_id?: string | null
}

export interface ResolveActionRequest {
  action_id: string
  decision: 'confirm' | 'cancel' | 'revise'
  comment?: string
}

export interface ResolveActionResult extends Record<string, unknown> {
  type: string
  status: string
  data: Record<string, unknown>
}

export interface ResolveActionResponse {
  dialog_state: DialogState
  action_result: ResolveActionResult
  message: string
  ui_hint: UiHint | null
  refresh_targets: RefreshTarget[]
}

export interface BackgroundTaskResponse {
  task_id: string
  task_type: string
  status: string
  result: any
  error: string | null
  ui_hint: UiHint
  refresh_targets: RefreshTarget[]
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface ChatHistoryMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type?: ChatMessageType | null
  meta?: Record<string, unknown> | null
  pending_action?: PendingAction | null
  diagnosis?: ProjectDiagnosis | null
  action_result?: Record<string, unknown> | null
  trace_id?: string | null
  content_truncated?: boolean
  original_content_length?: number
  created_at?: string | null
}

export interface MessageQuery {
  limit?: number
  after_id?: string
}

export type ModelTraceStatus = 'running' | 'success' | 'failed' | string

export interface TraceSource {
  source_type: string
  source_id?: string | null
  label?: string | null
  chapter_index?: number | null
  source_ref?: string | null
  title?: string | null
  metadata: Record<string, unknown>
}

export interface ContextBlock {
  key: string
  kind: string
  title: string
  content: string
  sources: TraceSource[]
  char_count: number
  token_estimate: number
  original_char_count?: number | null
  truncated: boolean
}

export interface PromptMetadata {
  prompt_id?: string | null
  prompt_version?: string | null
  template_name?: string | null
  template_hash?: string | null
}

export interface PromptBudget {
  max_context_chars?: number | null
  requested_context_chars?: number
  used_context_chars?: number
  remaining_context_chars?: number
  included_blocks: number
  omitted_blocks: number
  omitted_block_keys: string[]
  truncated_blocks: string[]
  has_omitted_blocks?: boolean
  has_truncated_blocks?: boolean
}

export interface ModelCallTraceListItem {
  id: string
  project_id: string
  trace_type: string
  status: ModelTraceStatus
  model?: string | null
  prompt_tokens?: number | null
  completion_tokens?: number | null
  latency_ms?: number | null
  error_message?: string | null
  dialog_id?: string | null
  request_message_id?: string | null
  response_message_id?: string | null
  chapter_id?: string | null
  chapter_index?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ModelCallTraceDetail extends ModelCallTraceListItem {
  temperature?: number | null
  max_tokens?: number | null
  messages: Array<Record<string, unknown>>
  context_blocks: ContextBlock[]
  trace_metadata: Record<string, unknown>
  prompt_metadata?: PromptMetadata | null
  prompt_budget?: PromptBudget | null
}

export interface PaginatedModelCallTraces {
  total: number
  items: ModelCallTraceListItem[]
}

export interface ModelCallTraceListParams {
  trace_type?: string
  chapter_index?: number
  dialog_id?: string
  limit?: number
  offset?: number
}

export interface SetupCharacter {
  name: string
  age?: number | null
  gender?: string | null
  personality?: string | null
  background?: string | null
  goals?: string | null
  character_status?: string | null
}

export interface SetupWorldBuilding {
  background?: string | null
  geography?: string | null
  society?: string | null
  rules?: string | null
  atmosphere?: string | null
}

export interface SetupCoreConcept {
  theme?: string | null
  premise?: string | null
  hook?: string | null
  unique_selling_point?: string | null
}

export interface SetupData {
  id: string
  project_id: string
  world_building: SetupWorldBuilding
  characters: SetupCharacter[]
  core_concept: SetupCoreConcept
  status: string
  created_at: string
  updated_at: string
}

export interface ProjectProfileVersion {
  id: string
  project_id: string
  genre_profile_id: string
  version: number
  contract_version: string
  profile_payload: Record<string, unknown>
  created_at: string
}

export interface WorldProjectionEntity {
  entity_type: string
  attributes: Record<string, unknown>
}

export interface WorldProjectionPresence {
  location_ref?: string
  presence_status?: string
  [key: string]: unknown
}

export interface WorldProjection {
  view_type: string
  entities: Record<string, WorldProjectionEntity>
  entities_total?: number
  entities_offset?: number
  entities_limit?: number
  entities_has_more?: boolean
  relations: Record<string, unknown>
  relations_total?: number
  relations_offset?: number
  relations_limit?: number
  relations_has_more?: boolean
  presence: Record<string, WorldProjectionPresence>
  presence_total?: number
  presence_offset?: number
  presence_limit?: number
  presence_has_more?: boolean
  occurred_events: Record<string, unknown>
  occurred_events_total?: number
  occurred_events_offset?: number
  occurred_events_limit?: number
  occurred_events_has_more?: boolean
  event_links: Record<string, unknown>
  event_links_total?: number
  event_links_offset?: number
  event_links_limit?: number
  event_links_has_more?: boolean
  facts: Record<string, Record<string, unknown>>
  facts_total?: number
  facts_offset?: number
  facts_limit?: number
  facts_has_more?: boolean
}

export interface WorldFactClaim {
  id: string
  project_id: string
  project_profile_version_id?: string | null
  profile_version?: number | null
  contract_version: string
  claim_id: string
  chapter_index?: number | null
  intra_chapter_seq: number
  subject_ref: string
  predicate: string
  object_ref_or_value: unknown
  claim_layer: string
  claim_status: string
  perspective_ref?: string | null
  disclosed_to_refs: string[]
  valid_from_anchor_id?: string | null
  valid_to_anchor_id?: string | null
  source_event_ref?: string | null
  evidence_refs: string[]
  authority_type: string
  confidence: number
  notes: string
  created_at: string
}

export interface PaginatedWorldFactClaims {
  claims: WorldFactClaim[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface WorldModelOverview {
  project_profile: ProjectProfileVersion | null
  projection: WorldProjection | null
}

export interface WorldModelOverviewQuery {
  entity_offset?: number
  entity_limit?: number
  relation_offset?: number
  relation_limit?: number
  presence_offset?: number
  presence_limit?: number
  event_offset?: number
  event_limit?: number
  event_link_offset?: number
  event_link_limit?: number
  fact_subject_offset?: number
  fact_subject_limit?: number
}

export interface WorldModelDashboardMetrics {
  entity_count: number
  fact_count: number
  presence_count: number
  event_count: number
  pending_bundle_count: number
  pending_item_count: number
}

export interface WorldModelNextAction {
  action: string
  label: string
}

export interface WorldModelDashboard {
  project_profile: ProjectProfileVersion | null
  metrics: WorldModelDashboardMetrics
  next_action: WorldModelNextAction
}

export interface ProposalBundle {
  id: string
  project_id: string
  project_profile_version_id: string
  profile_version: number
  parent_bundle_id: string | null
  bundle_status: string
  title: string
  summary: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface ProposalEvidenceSpan {
  ref?: string
  text?: string
  matched_names?: string[]
}

export interface ProposalQuality {
  signal?: string
  confidence_band?: string
  review_priority?: string
}

export interface ProposalObjectValue extends Record<string, unknown> {
  evidence_span?: ProposalEvidenceSpan
  quality?: ProposalQuality
}

export interface ProposalItem {
  id: string
  bundle_id: string
  parent_item_id: string | null
  item_status: string
  claim_id: string
  chapter_index?: number | null
  intra_chapter_seq?: number
  subject_ref: string
  predicate: string
  object_ref_or_value: ProposalObjectValue | string | number | boolean | null
  claim_layer: string
  perspective_ref?: string | null
  disclosed_to_refs?: string[]
  valid_from_anchor_id?: string | null
  valid_to_anchor_id?: string | null
  source_event_ref?: string | null
  evidence_refs: string[]
  authority_type: string
  confidence: number
  notes?: string
  contract_version: string
  approved_claim_id: string | null
  created_by: string
  created_at: string
}

export interface ProposalReview {
  id: string
  bundle_id: string
  proposal_item_id: string | null
  review_action: string
  reviewer_ref: string
  reason: string
  evidence_refs: string[]
  edited_fields: Record<string, unknown>
  created_truth_claim_id: string | null
  rollback_to_review_id: string | null
  created_at: string
}

export interface ProposalImpactSnapshot {
  id: string
  bundle_id: string
  affected_subject_refs: string[]
  affected_predicates: string[]
  affected_truth_claim_ids: string[]
  candidate_item_ids: string[]
  summary: Record<string, unknown>
  created_at: string
}

export interface ProposalBundleDetail {
  bundle: ProposalBundle
  items: ProposalItem[]
  items_total?: number
  items_offset?: number
  items_limit?: number
  reviews: ProposalReview[]
  impact_snapshots: ProposalImpactSnapshot[]
  conflicts: ProposalItemConflict[]
}

export interface ProposalReviewQueueCluster {
  cluster_id: string
  risk_level: 'high' | 'medium' | 'low' | string
  review_mode: 'individual' | 'batch' | string
  candidate_count: number
  item_ids: string[]
  bundle_ids: string[]
  subject_refs: string[]
  predicate: string
  chapter_range: { start: number | null; end: number | null }
  reason: string
}

export interface ProposalReviewQueue {
  project_id: string
  profile_version: number | null
  total_items: number
  returned_items?: number
  offset?: number
  limit?: number
  has_more?: boolean
  clusters: ProposalReviewQueueCluster[]
}

export interface ProposalReviewQueueQuery {
  offset?: number
  limit?: number
}

export interface ProposalReviewRequest {
  reviewer_ref: string
  action: 'approve' | 'approve_with_edits' | 'reject' | 'mark_uncertain'
  reason: string
  evidence_refs: string[]
  edited_fields: Record<string, unknown>
}

export interface ProposalSplitRequest {
  reviewer_ref: string
  reason: string
  evidence_refs: string[]
  item_ids: string[]
}

export interface ProposalRollbackRequest {
  reviewer_ref: string
  reason: string
  evidence_refs: string[]
}

export interface PaginatedProposalBundles {
  items: ProposalBundle[]
  total: number
  offset: number
  limit: number
}

export interface ProposalItemConflict {
  item_id: string
  conflict_type: 'truth_conflict' | 'high_impact'
  detail: string
  existing_claim_id: string | null
}

export interface AthenaOntology {
  entities: Record<string, {
    id: string
    canonical_id?: string
    primary_alias?: string
    aliases?: unknown[]
    name: string
    [key: string]: unknown
  }[]>
  relations: { id: string; source_ref: string; target_ref: string; relation_type: string }[]
  rules: { id: string; rule_id: string; description: string }[]
  setup_summary: {
    characters: unknown
    world_building: unknown
    core_concept: unknown
  } | null
  profile_version: number | null
  pagination?: {
    entities?: Record<string, {
      total: number
      offset: number
      limit: number
      has_more: boolean
    }>
    relations?: {
      total: number
      offset: number
      limit: number
      has_more: boolean
    }
    rules?: {
      total: number
      offset: number
      limit: number
      has_more: boolean
    }
  }
}

export interface AthenaOntologyQuery {
  entity_offset?: number
  entity_limit?: number
  relation_offset?: number
  relation_limit?: number
  rule_offset?: number
  rule_limit?: number
}

export interface AthenaTopologyWindowQuery {
  node_offset?: number
  node_limit?: number
  edge_offset?: number
  edge_limit?: number
}

export interface AthenaTimeline {
  anchors: { id: string; anchor_id: string; chapter_index: number; intra_chapter_seq: number; label: string }[]
  events: { id: string; event_id: string; chapter_index: number; intra_chapter_seq: number; event_type: string; description: string }[]
  anchors_total?: number
  anchors_offset?: number
  anchors_limit?: number
  anchors_has_more?: boolean
  events_total?: number
  events_offset?: number
  events_limit?: number
  events_has_more?: boolean
  latest?: boolean
}

export interface AthenaEvolutionPlan {
  outline: {
    id: string
    status: string
    total_chapters: number
    chapters: unknown
    plotlines: unknown
    chapters_total?: number
    chapters_offset?: number
    chapters_limit?: number
    chapters_has_more?: boolean
    plotlines_total?: number
    plotlines_offset?: number
    plotlines_limit?: number
    plotlines_has_more?: boolean
  } | null
  storyline: {
    id: string
    status: string
    plotlines: unknown
    foreshadowing: unknown
    plotlines_total?: number
    plotlines_offset?: number
    plotlines_limit?: number
    plotlines_has_more?: boolean
    foreshadowing_total?: number
    foreshadowing_offset?: number
    foreshadowing_limit?: number
    foreshadowing_has_more?: boolean
  } | null
}

export interface AthenaEvolutionPlanQuery {
  mode?: 'full' | 'window'
  chapter_offset?: number
  chapter_limit?: number
  plotline_offset?: number
  plotline_limit?: number
  milestone_offset?: number
  milestone_limit?: number
  foreshadowing_offset?: number
  foreshadowing_limit?: number
}

export interface AthenaImportSetupResult {
  status: string
  profile_version: number
  project_profile_version_id: string
  created: {
    profile: number
    characters: number
    locations: number
    factions: number
    artifacts: number
    rules: number
  }
}

export interface AthenaSetupImportPreviewCandidate {
  name: string
  canonical_id: string
  source: string
  description: string
}

export interface AthenaSetupImportPreview {
  status: string
  project_profile_exists: boolean
  profile_version: number | null
  would_create: {
    profile: number
    characters: number
    locations: number
    factions: number
    artifacts: number
    rules: number
  }
  candidates: {
    characters: AthenaSetupImportPreviewCandidate[]
    locations: AthenaSetupImportPreviewCandidate[]
    factions: AthenaSetupImportPreviewCandidate[]
    artifacts: AthenaSetupImportPreviewCandidate[]
    rules: AthenaSetupImportPreviewCandidate[]
  }
}

export interface AthenaAnalyzeChapterResult {
  status: string
  reason?: string | null
  chapter_index: number
  task_id: string | null
  proposal_bundle_id: string | null
  created: { proposal_items: number }
  updated: { proposal_items: number }
  skipped: { duplicates: number }
}

export interface AthenaChapterContext {
  chapter_index: number
  profile_version: number | null
  project_profile_version_id: string | null
  sections: { key: string; title: string; items: unknown[] }[]
  prompt_context: string
}

export interface AthenaConsistencyIssue {
  id?: string
  project_id?: string
  chapter_index?: number
  checker_name?: string
  severity?: string
  status?: string
  check_type?: string
  type?: string
  description?: string
  message?: string
  evidence?: string | Record<string, unknown>
}

export interface AthenaConsistencyIssueListResponse {
  issues: AthenaConsistencyIssue[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface AthenaRetrievalIndexResult {
  status: string
  project_id: string
  chapter_index: number | null
  indexed: {
    documents: number
    chunks: number
    terms: number
    embeddings: number
  }
}

export interface AthenaRetrievalDiagnostics {
  project_id: string
  embedding_provider: string
  embedding_model: string
  vector_dimension: number
  total_documents: number
  total_chunks: number
  total_terms: number
  total_embeddings: number
  documents_by_source_type: Record<string, number>
}

export interface LongformMaintenanceDiagnostics {
  project_id: string
  status: string
  chapter_count: number
  word_target?: LongformWordTargetDiagnostics
  stale_memory_count: number
  missing_memory_count: number
  stale_retrieval_count: number
  missing_retrieval_count: number
  stale_chapter_indexes: number[]
  missing_memory_chapter_indexes: number[]
  stale_retrieval_chapter_indexes: number[]
  missing_retrieval_chapter_indexes: number[]
  latest_chapter_updated_at: string | null
  latest_memory_updated_at: string | null
  latest_retrieval_updated_at: string | null
  latest_synced_chapter_index: number | null
}

export interface LongformWordTargetDiagnostics {
  status: string
  target_average_word_count?: number | null
  target_min_word_count?: number | null
  target_max_word_count?: number | null
  under_target_count: number
  within_target_count: number
  over_target_count: number
  under_target_chapter_indexes: number[]
  over_target_chapter_indexes: number[]
}

export interface LongformMaintenanceRepairResult {
  project_id: string
  status: string
  repaired_memory_count: number
  repaired_retrieval_count: number
  refreshed_chapter_indexes: number[]
  synced_scope_keys: string[]
  has_more: boolean
  remaining_issue_count: number
  remaining: LongformMaintenanceDiagnostics
}

export interface AthenaRetrievalSearchItem {
  chunk_id: string
  document_id: string
  source_type: string
  source_ref: string
  title: string
  chapter_index: number | null
  score: number
  lexical_score: number
  vector_score: number
  snippet: string
  metadata: Record<string, unknown>
}

export interface AthenaRetrievalSearchResponse {
  query: string
  total: number
  items: AthenaRetrievalSearchItem[]
}

export interface ChapterContent {
  id: string
  project_id: string
  chapter_index: number
  title: string
  content: string
  word_count: number
  status: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  generation_time: number
  temperature: number
  last_generation_trace_id?: string | null
  created_at: string
  updated_at: string
}

export interface RevisionAnnotationPayload {
  paragraph_index: number
  start_offset: number
  end_offset: number
  selected_text: string
  comment: string
}

export interface RevisionCorrectionPayload {
  paragraph_index: number
  original_text: string
  corrected_text: string
}

export interface ChapterRevisionPayload {
  chapter_index: number
  annotations: RevisionAnnotationPayload[]
  corrections: RevisionCorrectionPayload[]
}

export interface ChapterRevisionDraftPayload {
  annotations: RevisionAnnotationPayload[]
  corrections: RevisionCorrectionPayload[]
}

export interface RevisionAnnotation extends RevisionAnnotationPayload {
  id: string
  revision_id: string
}

export interface RevisionCorrection extends RevisionCorrectionPayload {
  id: string
  revision_id: string
}

export interface ChapterRevision {
  id: string
  project_id: string
  chapter_id: string
  chapter_index: number
  revision_index: number
  status: string
  submitted_at: string | null
  completed_at: string | null
  base_version_id: string | null
  result_version_id: string | null
  annotations: RevisionAnnotation[]
  corrections: RevisionCorrection[]
}

export interface ChapterRevisionListResponse {
  revisions: ChapterRevision[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface AthenaOptimization {
  rules: {
    id: string
    rule_type: string
    condition: string
    action: string
    priority: number
    hit_count: number
    created_at: string
  }[]
  style_config: Record<string, unknown>
  learning_logs: {
    rule_id: string
    event_type: string
    summary: string
    created_at: string
  }[]
  rules_total?: number
  rules_offset?: number
  rules_limit?: number
  rules_has_more?: boolean
}

export interface AthenaOptimizationQuery {
  rules_offset?: number
  rules_limit?: number
}
