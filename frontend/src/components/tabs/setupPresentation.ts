import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'

export const EMPTY_SETUP_TEXT = '待补充'

type SetupSection = {
  key: string
  label: string
  value: string
}

function normalizeText(value: string | null | undefined): string {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || EMPTY_SETUP_TEXT
}

export function buildCharacterSummary(character: SetupCharacter): string {
  const candidates = [character.background, character.personality, character.goals]

  for (const candidate of candidates) {
    const text = typeof candidate === 'string' ? candidate.trim() : ''
    if (text) {
      return text
    }
  }

  return EMPTY_SETUP_TEXT
}

export function getCharacterMeta(character: SetupCharacter): string[] {
  const meta: string[] = []

  if (character.age !== null && character.age !== undefined) {
    meta.push(`${character.age} 岁`)
  }

  const genderMap: Record<string, string> = {
    male: '男',
    female: '女',
  }
  const gender = typeof character.gender === 'string' ? character.gender.trim().toLowerCase() : ''
  if (gender) {
    meta.push(genderMap[gender] ?? character.gender!.trim())
  }

  const statusMap: Record<string, string> = {
    alive: '存活',
    dead: '死亡',
  }
  const rawStatus = typeof character.character_status === 'string' ? character.character_status.trim() : ''
  const status = rawStatus.toLowerCase()
  if (status) {
    meta.push(statusMap[status] ?? rawStatus)
  }

  return meta
}

export function getWorldSections(world: SetupWorldBuilding): SetupSection[] {
  return [
    { key: 'background', label: '时代背景', value: normalizeText(world.background) },
    { key: 'geography', label: '地理格局', value: normalizeText(world.geography) },
    { key: 'society', label: '社会结构', value: normalizeText(world.society) },
    { key: 'rules', label: '规则体系', value: normalizeText(world.rules) },
    { key: 'atmosphere', label: '氛围基调', value: normalizeText(world.atmosphere) },
  ]
}

export function getConceptSections(concept: SetupCoreConcept): SetupSection[] {
  return [
    { key: 'theme', label: '主题', value: normalizeText(concept.theme) },
    { key: 'premise', label: '前提设定', value: normalizeText(concept.premise) },
    { key: 'hook', label: '核心钩子', value: normalizeText(concept.hook) },
    { key: 'unique_selling_point', label: '独特卖点', value: normalizeText(concept.unique_selling_point) },
  ]
}
