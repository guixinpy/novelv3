import { describe, expect, it } from 'vitest'
import { summarizeWorkspaceRequests, type WorkspaceRequestRecord } from './workspacePerfProbe'

describe('workspace perf probe', () => {
  it('groups request counts and durations by phase', () => {
    const records: WorkspaceRequestRecord[] = [
      { phase: 'athena_to_hermes', method: 'GET', url: '/api/v1/projects/1', status: 200, durationMs: 20 },
      { phase: 'athena_to_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 30 },
      { phase: 'hermes_to_athena', method: 'GET', url: '/api/v1/projects/1/athena/ontology', status: 200, durationMs: 40 },
    ]

    const summary = summarizeWorkspaceRequests(records)

    expect(summary.athena_to_hermes.requestCount).toBe(2)
    expect(summary.athena_to_hermes.totalDurationMs).toBe(50)
    expect(summary.hermes_to_athena.urls).toEqual(['/api/v1/projects/1/athena/ontology'])
  })

  it('marks duplicate URLs inside a phase', () => {
    const records: WorkspaceRequestRecord[] = [
      { phase: 'return_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 10 },
      { phase: 'return_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 15 },
    ]

    const summary = summarizeWorkspaceRequests(records)

    expect(summary.return_hermes.duplicateUrls).toEqual(['/api/v1/projects/1/chapters'])
  })
})
