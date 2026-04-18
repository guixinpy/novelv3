export type ChatCommandName = 'clear' | 'compact' | 'setup' | 'storyline' | 'outline'

export interface ChatCommandDefinition {
  name: ChatCommandName
  description: string
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
  { name: 'clear', description: '清空聊天上下文并重置会话' },
  { name: 'compact', description: '压缩会话历史为摘要' },
  { name: 'setup', description: '生成或更新世界设定' },
  { name: 'storyline', description: '生成或更新剧情线' },
  { name: 'outline', description: '生成或更新章节大纲' },
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
  const prefix = query.slice(1).trim().toLowerCase()
  if (!prefix) return chatCommandRegistry
  return chatCommandRegistry.filter((command) => command.name.startsWith(prefix))
}
