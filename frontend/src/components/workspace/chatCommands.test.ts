import { describe, expect, it } from 'vitest'
import { filterChatCommands, parseSlashCommand } from './chatCommands'

describe('chatCommands', () => {
  it('已注册命令会被解析为 command', () => {
    const parsed = parseSlashCommand('/setup 主角是植物学家')
    expect(parsed).toEqual({
      kind: 'command',
      name: 'setup',
      args: '主角是植物学家',
      rawInput: '/setup 主角是植物学家',
    })
  })

  it('未知 slash 会回退为 text', () => {
    const parsed = parseSlashCommand('/foo bar')
    expect(parsed).toEqual({
      kind: 'text',
      text: '/foo bar',
    })
  })

  it('prefix 过滤 /co 只返回 compact', () => {
    const result = filterChatCommands('/co')
    expect(result).toEqual([
      expect.objectContaining({
        name: 'compact',
      }),
    ])
  })
})
