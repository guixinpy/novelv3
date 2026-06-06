import { numberValue, stringValue } from './safeProjection'

export function contextCompressionStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'warning') return '警告'
  if (value === 'blocked') return '已阻塞'
  if (value === 'completed' || value === 'success') return '已完成'
  return value || '未知'
}

export function contextCompressionSeverityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'warning') return '警告'
  if (value === 'error') return '错误'
  if (value === 'info') return '信息'
  return value
}

export function contextCompressionChapterLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

export function safeContextCompressionText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|memory-secret|longform-memory-secret|source-secret|critical-secret|source_refs?|source_type|source_id|source_sections?|source_section_keys|memory_provenance|LongformMemory|phase\d+\.agent_context_compression|runtime_behavior_changed|include_prompt_context|context_guard_failure_count|compressed_context|SECRET_COMPRESSED_CONTEXT|prompt context raw|scope_key|suggested_params|load_agent_context_compression_summary|secret-preflight-budget-version/i.test(value)) return ''
  return value.slice(0, 120)
}
