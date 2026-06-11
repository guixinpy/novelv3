import { describe, expect, it } from 'vitest'

import { parseSseChunk, type AgentStreamEvent } from './agentV2'

function frame(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
}

describe('parseSseChunk', () => {
  it('parses complete frames and keeps the incomplete tail', () => {
    const buffer =
      frame('assistant_delta', { text: '你好' }) +
      frame('assistant_delta', { text: '，作者' }) +
      'event: turn_ended\ndata: {"stop_reason"'
    const { events, rest } = parseSseChunk(buffer)
    expect(events).toHaveLength(2)
    expect(events[0]).toEqual({ event: 'assistant_delta', data: { text: '你好' } })
    expect(rest).toContain('turn_ended')
  })

  it('returns empty events for pure partial chunk', () => {
    const { events, rest } = parseSseChunk('event: assistant_delta\ndata: {"te')
    expect(events).toHaveLength(0)
    expect(rest).toBe('event: assistant_delta\ndata: {"te')
  })

  it('parses tool call events', () => {
    const buffer =
      frame('tool_call_started', { id: 'c1', name: 'read_chapter', arguments: { chapter_index: 1 } }) +
      frame('tool_call_finished', { id: 'c1', name: 'read_chapter', is_error: false, result_text: '{}' })
    const { events } = parseSseChunk(buffer)
    expect(events.map((e: AgentStreamEvent) => e.event)).toEqual([
      'tool_call_started',
      'tool_call_finished',
    ])
  })

  it('skips malformed frames without throwing', () => {
    const buffer = 'event: assistant_delta\ndata: {not json}\n\n' + frame('assistant_delta', { text: 'ok' })
    const { events } = parseSseChunk(buffer)
    expect(events).toHaveLength(1)
    expect(events[0].data).toEqual({ text: 'ok' })
  })
})
