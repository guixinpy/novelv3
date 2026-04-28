import type { ProjectDiagnosis, RefreshTarget } from '../api/types'

export type HydrationSnapshot = {
  projectId: string
  version: number
}

export type HydrationTracker = {
  currentProjectId: string
  version: number
  targets: Set<RefreshTarget>
}

const INITIAL_OPTIONAL_TARGETS: RefreshTarget[] = ['setup', 'storyline', 'outline']

export function createHydrationTracker(): HydrationTracker {
  return {
    currentProjectId: '',
    version: 0,
    targets: new Set<RefreshTarget>(),
  }
}

export function beginHydration(tracker: HydrationTracker, projectId: string): HydrationSnapshot {
  tracker.version += 1
  tracker.currentProjectId = projectId
  tracker.targets.clear()
  return {
    projectId,
    version: tracker.version,
  }
}

export function isActiveHydrationSnapshot(tracker: HydrationTracker, snapshot: HydrationSnapshot) {
  return tracker.currentProjectId === snapshot.projectId && tracker.version === snapshot.version
}

export function markHydratedTarget(
  tracker: HydrationTracker,
  snapshot: HydrationSnapshot,
  target: RefreshTarget,
) {
  if (!isActiveHydrationSnapshot(tracker, snapshot)) return false
  tracker.targets.add(target)
  return true
}

export function markHydratedTargets(
  tracker: HydrationTracker,
  snapshot: HydrationSnapshot,
  targets: RefreshTarget[],
) {
  if (!isActiveHydrationSnapshot(tracker, snapshot)) return []
  for (const target of targets) {
    tracker.targets.add(target)
  }
  return targets
}

export function getInitialProjectHydrationTargets(diagnosis: ProjectDiagnosis | null | undefined): RefreshTarget[] {
  const completed = new Set(diagnosis?.completed_items || [])
  return INITIAL_OPTIONAL_TARGETS.filter((target) => completed.has(target))
}
