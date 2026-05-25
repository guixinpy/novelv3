import { describe, expect, it } from 'vitest'
import { filterChatCommands, normalizeChatCommandDefinitions, parseSlashCommand } from './chatCommands'

describe('chatCommands', () => {
  it('公开候选只展示 Agent 控制命令和会话命令', () => {
    expect(filterChatCommands('/').map((command) => command.name)).toEqual([
      'continue',
      'status',
      'clear',
      'compact',
    ])
  })

  it('/continue 和 /status 会被解析为 Agent 控制命令', () => {
    expect(parseSlashCommand('/continue')).toEqual({
      kind: 'command',
      name: 'continue',
      args: '',
      rawInput: '/continue',
    })
    expect(parseSlashCommand('/status')).toEqual({
      kind: 'command',
      name: 'status',
      args: '',
      rawInput: '/status',
    })
  })

  it('可从后端目录规范化命令定义并驱动解析与过滤', () => {
    const commands = normalizeChatCommandDefinitions([
      {
        name: 'continue',
        label: '/continue',
        description: '继续',
        example: '/continue',
        supports_args: false,
        public: true,
        category: 'agent_control',
        capability_id: 'agent.continue',
        control_projection_type: 'continue_agent_control',
        required_agent_tools: ['inspect_agent_health_projection'],
        available: false,
        unavailable_reasons: ['缺少 Agent 工具适配器：inspect_agent_health_projection'],
      },
      {
        name: 'memory',
        label: '/memory',
        description: '记忆',
        example: '/memory',
        supports_args: false,
        public: true,
        category: 'agent_control',
        capability_id: 'agent.memory',
        required_agent_tools: [],
        available: true,
      },
      {
        name: 'chapter',
        label: '/chapter',
        description: '旧命令',
        example: '/chapter 1',
        supports_args: true,
        public: false,
        legacy: true,
      },
    ])

    expect(commands[0]).toMatchObject({
      name: 'continue',
      category: 'agent_control',
      capabilityId: 'agent.continue',
      controlProjectionType: 'continue_agent_control',
      requiredAgentTools: ['inspect_agent_health_projection'],
      available: false,
      unavailableReasons: ['缺少 Agent 工具适配器：inspect_agent_health_projection'],
    })
    expect(filterChatCommands('/m', commands).map((command) => command.name)).toEqual(['memory'])
    expect(parseSlashCommand('/memory', commands)).toMatchObject({ kind: 'command', name: 'memory' })
    expect(filterChatCommands('/con', commands)).toEqual([])
    expect(filterChatCommands('/ch', commands)).toEqual([])
    expect(parseSlashCommand('/chapter 1', commands)).toMatchObject({ kind: 'command', name: 'chapter' })
  })

  it('已注册命令会被解析为 command', () => {
    const parsed = parseSlashCommand('/setup 主角是植物学家')
    expect(parsed).toEqual({
      kind: 'command',
      name: 'setup',
      args: '主角是植物学家',
      rawInput: '/setup 主角是植物学家',
    })
  })

  it('/chapter 会被解析为章节生成命令', () => {
    const parsed = parseSlashCommand('/chapter 1 强化灯塔悬疑')
    expect(parsed).toEqual({
      kind: 'command',
      name: 'chapter',
      args: '1 强化灯塔悬疑',
      rawInput: '/chapter 1 强化灯塔悬疑',
    })
  })

  it('未知 slash 会回退为 text', () => {
    const parsed = parseSlashCommand('/foo bar')
    expect(parsed).toEqual({
      kind: 'text',
      text: '/foo bar',
    })
  })

  it('prefix 过滤 /co 返回 continue 与 compact', () => {
    const result = filterChatCommands('/co')
    expect(result.map((command) => command.name)).toEqual(['continue', 'compact'])
    expect(filterChatCommands('/com')).toEqual([
      expect.objectContaining({ name: 'compact' }),
    ])
  })

  it('旧模块命令不出现在候选中', () => {
    expect(filterChatCommands('/ch')).toEqual([])
    expect(filterChatCommands('/setup')).toEqual([])
    expect(filterChatCommands('/storyline')).toEqual([])
    expect(filterChatCommands('/outline')).toEqual([])
  })

  it('/ setup 不应出现在候选中，且 parser 仍按普通文本处理', () => {
    expect(filterChatCommands('/ setup')).toEqual([])
    expect(parseSlashCommand('/ setup')).toEqual({
      kind: 'text',
      text: '/ setup',
    })
  })
})
