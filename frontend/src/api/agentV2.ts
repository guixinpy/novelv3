// /api/v2 Agent 会话客户端（对齐后端契约：二轮 code-review R4 修复路径/字段）

export interface AgentSessionMeta {
  session_id: string
  project_id: string
}

export type AgentStreamEvent =
  | { event: 'assistant_delta'; data: { text: string } }
  | { event: 'assistant_message'; data: { content: string; tool_call_names: string[] } }
  | { event: 'tool_started'; data: { call_id: string; name: string; arguments: unknown } }
  | { event: 'tool_finished'; data: { call_id: string; name: string; is_error: boolean; result_text: string } }
  | { event: 'approval_pending'; data: { call_id: string; name: string; arguments: unknown } }
  | {
      event: 'turn_ended'
      data: { stop_reason: string; iterations: number; prompt_tokens: number; completion_tokens: number }
    }
  | { event: 'agent_start' | 'agent_end' | 'turn_start' | 'guard_tripped' | 'compaction'; data: Record<string, unknown> }

const BASE = '/api/v2'

async function requireOk(resp: Response): Promise<Response> {
  if (!resp.ok) {
    const body = await resp.text().catch(() => '')
    throw new Error(`HTTP ${resp.status}: ${body.slice(0, 300)}`)
  }
  return resp
}

export async function createProject(name: string, genre = ''): Promise<{ id: string; name: string }> {
  const resp = await requireOk(
    await fetch(`${BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, genre }),
    }),
  )
  return resp.json()
}

export async function createAgentSession(projectId: string): Promise<AgentSessionMeta> {
  const resp = await requireOk(
    await fetch(`${BASE}/agent/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    }),
  )
  return resp.json()
}

/** 解析 SSE 文本块（可能含多个事件帧），返回完整事件与剩余未完整片段。 */
export function parseSseChunk(buffer: string): { events: AgentStreamEvent[]; rest: string } {
  const events: AgentStreamEvent[] = []
  const frames = buffer.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const frame of frames) {
    let eventName = ''
    let dataLine = ''
    for (const line of frame.split('\n')) {
      if (line.startsWith('event: ')) eventName = line.slice('event: '.length).trim()
      else if (line.startsWith('data: ')) dataLine = line.slice('data: '.length)
    }
    if (!eventName || !dataLine) continue
    try {
      events.push({ event: eventName, data: JSON.parse(dataLine) } as AgentStreamEvent)
    } catch {
      // 跳过无法解析的帧
    }
  }
  return { events, rest }
}

export async function approveTool(sessionId: string, callId: string): Promise<{ approved: boolean }> {
  const resp = await requireOk(
    await fetch(`${BASE}/agent/sessions/${sessionId}/approve?call_id=${encodeURIComponent(callId)}`, {
      method: 'POST',
    }),
  )
  return resp.json()
}

export async function rejectTool(sessionId: string, callId: string, reason = ''): Promise<{ approved: boolean }> {
  const resp = await requireOk(
    await fetch(`${BASE}/agent/sessions/${sessionId}/reject?call_id=${encodeURIComponent(callId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    }),
  )
  return resp.json()
}

export async function getPendingApprovals(
  sessionId: string,
): Promise<{ pending: { call_id: string; name: string; arguments: unknown }[] }> {
  const resp = await requireOk(await fetch(`${BASE}/agent/sessions/${sessionId}/pending-approvals`))
  return resp.json()
}

export async function streamAgentMessage(
  sessionId: string,
  content: string,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await requireOk(
    await fetch(`${BASE}/agent/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
      signal,
    }),
  )
  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const { events, rest } = parseSseChunk(buffer)
    buffer = rest
    for (const event of events) onEvent(event)
  }
}
