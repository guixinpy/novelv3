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
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type?: ChatMessageType | null
  meta?: Record<string, unknown> | null
  pending_action?: PendingAction | null
  diagnosis?: ProjectDiagnosis | null
  action_result?: Record<string, unknown> | null
  created_at?: string | null
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
  relations: Record<string, unknown>
  presence: Record<string, WorldProjectionPresence>
  occurred_events: Record<string, unknown>
  event_links: Record<string, unknown>
  facts: Record<string, Record<string, unknown>>
}

export interface WorldModelOverview {
  project_profile: ProjectProfileVersion | null
  projection: WorldProjection | null
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

export interface ProposalItem {
  id: string
  bundle_id: string
  parent_item_id: string | null
  item_status: string
  claim_id: string
  subject_ref: string
  predicate: string
  object_ref_or_value: unknown
  claim_layer: string
  evidence_refs: string[]
  authority_type: string
  confidence: number
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
  reviews: ProposalReview[]
  impact_snapshots: ProposalImpactSnapshot[]
  conflicts: ProposalItemConflict[]
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
  entities: Record<string, { id: string; name: string }[]>
  relations: { id: string; source_ref: string; target_ref: string; relation_type: string }[]
  rules: { id: string; rule_id: string; description: string }[]
  setup_summary: {
    characters: unknown
    world_building: unknown
    core_concept: unknown
  } | null
  profile_version: number | null
}

export interface AthenaTimeline {
  anchors: { id: string; anchor_id: string; chapter_index: number; intra_chapter_seq: number; label: string }[]
  events: { id: string; event_id: string; chapter_index: number; intra_chapter_seq: number; event_type: string; description: string }[]
}

export interface AthenaEvolutionPlan {
  outline: { id: string; status: string; total_chapters: number; chapters: unknown; plotlines: unknown } | null
  storyline: { id: string; status: string; plotlines: unknown; foreshadowing: unknown } | null
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
}
