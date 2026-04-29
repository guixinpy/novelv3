export interface WorkspaceRequestRecord {
  phase: string
  method: string
  url: string
  status: number | string
  durationMs: number
}

export interface WorkspacePhaseSummary {
  requestCount: number
  totalDurationMs: number
  urls: string[]
  duplicateUrls: string[]
}

export function summarizeWorkspaceRequests(records: WorkspaceRequestRecord[]) {
  const summary: Record<string, WorkspacePhaseSummary> = {}

  for (const record of records) {
    const phase = record.phase || 'unknown'
    const item = summary[phase] ?? {
      requestCount: 0,
      totalDurationMs: 0,
      urls: [],
      duplicateUrls: [],
    }
    item.requestCount += 1
    item.totalDurationMs += record.durationMs
    item.urls.push(record.url)
    summary[phase] = item
  }

  for (const item of Object.values(summary)) {
    const counts = new Map<string, number>()
    for (const url of item.urls) counts.set(url, (counts.get(url) || 0) + 1)
    item.duplicateUrls = [...counts.entries()]
      .filter(([, count]) => count > 1)
      .map(([url]) => url)
  }

  return summary
}
