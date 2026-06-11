// /api/v2 Agent 会话客户端（M1 最小实现，独立于 v1 client.ts）

export interface AgentSessionMeta {
  session_id: string
  project_id: string
}

export interface AgentMessage {
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string | null
  tool_calls?: { id: string; function: { name: string; arguments: string } }[]
  tool_call_id?: string
}

export type AgentStreamEvent =
  | { event: 'assistant_delta'; data: { text: string } }
  | { event: 'assistant_message'; data: { content: string; tool_call_names: string[] } }
  | { event: 'tool_call_started'; data: { id: string; name: string; arguments: unknown } }
  | { event: 'tool_call_finished'; data: { id: string; name: string; is_error: boolean; result_text: string } }
  | {
      event: 'turn_ended'
      data: { stop_reason: string; iterations: number; usage: { prompt_tokens: number; completion_tokens: number } }
    }

const BASE = '/api/v2'

async function requireOk(resp: Response): Promise<Response> {
  if (!resp.ok) {
    const body = await resp.text().catch(() => '')
    throw new Error(`HTTP ${resp.status}: ${body.slice(0, 300)}`)
  }
  return resp
}

export async function createAgentSession(projectId: string): Promise<AgentSessionMeta> {
  const resp = await requireOk(
    await fetch(`${BASE}/projects/${projectId}/sessions`, { method: 'POST' }),
  )
  return resp.json()
}

export async function getAgentSession(
  sessionId: string,
): Promise<AgentSessionMeta & { messages: AgentMessage[] }> {
  const resp = await requireOk(await fetch(`${BASE}/sessions/${sessionId}`))
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

export async function streamAgentMessage(
  sessionId: string,
  content: string,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await requireOk(
    await fetch(`${BASE}/sessions/${sessionId}/messages`, {
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
