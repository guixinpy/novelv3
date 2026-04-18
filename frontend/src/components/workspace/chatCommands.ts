export type ChatCommandName = 'clear' | 'compact' | 'setup' | 'storyline' | 'outline'

export interface ChatCommandDefinition {
  name: ChatCommandName
  label: string
  description: string
  example: string
  supportsArgs: boolean
}

export type ParsedSlashCommand =
  | {
    kind: 'command'
    name: ChatCommandName
    args: string
    rawInput: string
  }
  | {
    kind: 'text'
    text: string
  }

export const chatCommandRegistry: ChatCommandDefinition[] = [
  { name: 'clear', label: '/clear', description: '清空聊天上下文并重置会话', example: '/clear', supportsArgs: false },
  { name: 'compact', label: '/compact', description: '压缩会话历史为摘要', example: '/compact', supportsArgs: false },
  { name: 'setup', label: '/setup', description: '生成或更新世界设定', example: '/setup 主角是植物学家', supportsArgs: true },
  { name: 'storyline', label: '/storyline', description: '生成或更新剧情线', example: '/storyline 主线走悬疑反转', supportsArgs: true },
  { name: 'outline', label: '/outline', description: '生成或更新章节大纲', example: '/outline 第 1 章结尾必须反转', supportsArgs: true },
]

const registeredCommandNames = new Set(chatCommandRegistry.map((command) => command.name))

export function parseSlashCommand(input: string): ParsedSlashCommand {
  const commandMatch = input.match(/^\/([a-zA-Z]+)(?:\s+([\s\S]*))?$/)
  if (!commandMatch) {
    return { kind: 'text', text: input }
  }

  const name = commandMatch[1].toLowerCase() as ChatCommandName
  if (!registeredCommandNames.has(name)) {
    return { kind: 'text', text: input }
  }

  return {
    kind: 'command',
    name,
    args: commandMatch[2]?.trim() || '',
    rawInput: input,
  }
}

export function filterChatCommands(query: string): ChatCommandDefinition[] {
  if (!query.startsWith('/')) return []
  const match = query.match(/^\/([a-zA-Z]*)$/)
  if (!match) return []
  const prefix = match[1].toLowerCase()
  if (prefix.length === 0) return chatCommandRegistry
  return chatCommandRegistry.filter((command) => command.name.startsWith(prefix))
}
