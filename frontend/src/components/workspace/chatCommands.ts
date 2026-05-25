export type ChatCommandName = string

export interface ChatCommandDefinition {
  name: ChatCommandName
  label: string
  description: string
  example: string
  supportsArgs: boolean
  public: boolean
  category?: string
  capabilityId?: string
  requiredAgentTools?: string[]
  controlProjectionType?: string
  available: boolean
  unavailableReasons: string[]
  legacy?: boolean
}

export interface BackendChatCommandDefinition {
  name: string
  label?: string
  description?: string
  example?: string
  supports_args?: boolean
  supportsArgs?: boolean
  public?: boolean
  category?: string
  capability_id?: string
  capabilityId?: string
  required_agent_tools?: string[]
  requiredAgentTools?: string[]
  control_projection_type?: string
  controlProjectionType?: string
  available?: boolean
  unavailable_reasons?: string[]
  unavailableReasons?: string[]
  legacy?: boolean
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
  { name: 'continue', label: '/continue', description: '让写作 Agent 根据当前项目状态继续推进', example: '/continue', supportsArgs: false, public: true, category: 'agent_control', capabilityId: 'agent.continue', requiredAgentTools: [], controlProjectionType: 'continue_agent_control', available: true, unavailableReasons: [] },
  { name: 'status', label: '/status', description: '查看写作 Agent 对当前项目状态的判断', example: '/status', supportsArgs: false, public: true, category: 'agent_control', capabilityId: 'agent.status', requiredAgentTools: [], controlProjectionType: 'agent_health_projection', available: true, unavailableReasons: [] },
  { name: 'clear', label: '/clear', description: '清空聊天上下文并重置会话', example: '/clear', supportsArgs: false, public: true, category: 'session', capabilityId: 'session.clear', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [] },
  { name: 'compact', label: '/compact', description: '压缩会话历史为摘要', example: '/compact', supportsArgs: false, public: true, category: 'session', capabilityId: 'session.compact', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [] },
  { name: 'setup', label: '/setup', description: '旧命令：转译为 Agent 设定意图', example: '/setup 主角是植物学家', supportsArgs: true, public: false, category: 'legacy_alias', capabilityId: 'legacy.setup', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [], legacy: true },
  { name: 'storyline', label: '/storyline', description: '旧命令：转译为 Agent 故事线意图', example: '/storyline 主线走悬疑反转', supportsArgs: true, public: false, category: 'legacy_alias', capabilityId: 'legacy.storyline', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [], legacy: true },
  { name: 'outline', label: '/outline', description: '旧命令：转译为 Agent 大纲意图', example: '/outline 第 1 章结尾必须反转', supportsArgs: true, public: false, category: 'legacy_alias', capabilityId: 'legacy.outline', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [], legacy: true },
  { name: 'chapter', label: '/chapter', description: '旧命令：转译为 Agent 章节生成意图', example: '/chapter 1 强化灯塔悬疑', supportsArgs: true, public: false, category: 'legacy_alias', capabilityId: 'legacy.chapter', requiredAgentTools: [], controlProjectionType: '', available: true, unavailableReasons: [], legacy: true },
]

const registeredCommandNames = new Set(chatCommandRegistry.map((command) => command.name))

export function normalizeChatCommandDefinitions(commands: BackendChatCommandDefinition[]): ChatCommandDefinition[] {
  const normalized: ChatCommandDefinition[] = []
  for (const command of commands) {
    const name = String(command.name || '').trim().toLowerCase()
    if (!name) continue
    normalized.push({
      name,
      label: command.label || `/${name}`,
      description: command.description || '',
      example: command.example || `/${name}`,
      supportsArgs: Boolean(command.supportsArgs ?? command.supports_args),
      public: command.public !== false,
      category: command.category,
      capabilityId: command.capabilityId || command.capability_id,
      requiredAgentTools: command.requiredAgentTools || command.required_agent_tools || [],
      controlProjectionType: command.controlProjectionType ?? command.control_projection_type ?? '',
      available: command.available !== false,
      unavailableReasons: command.unavailableReasons || command.unavailable_reasons || [],
      legacy: command.legacy === true,
    })
  }
  return normalized
}

function commandNames(commands: ChatCommandDefinition[]) {
  if (commands === chatCommandRegistry) return registeredCommandNames
  return new Set(commands.map((command) => command.name))
}

export function parseSlashCommand(input: string, commands: ChatCommandDefinition[] = chatCommandRegistry): ParsedSlashCommand {
  const commandMatch = input.match(/^\/([a-zA-Z]+)(?:\s+([\s\S]*))?$/)
  if (!commandMatch) {
    return { kind: 'text', text: input }
  }

  const name = commandMatch[1].toLowerCase() as ChatCommandName
  if (!commandNames(commands).has(name)) {
    return { kind: 'text', text: input }
  }

  return {
    kind: 'command',
    name,
    args: commandMatch[2]?.trim() || '',
    rawInput: input,
  }
}

export function filterChatCommands(query: string, commands: ChatCommandDefinition[] = chatCommandRegistry): ChatCommandDefinition[] {
  if (!query.startsWith('/')) return []
  const match = query.match(/^\/([a-zA-Z]*)$/)
  if (!match) return []
  const prefix = match[1].toLowerCase()
  const publicCommands = commands.filter((command) => command.public && command.available !== false)
  if (prefix.length === 0) return publicCommands
  return publicCommands.filter((command) => command.name.startsWith(prefix))
}
