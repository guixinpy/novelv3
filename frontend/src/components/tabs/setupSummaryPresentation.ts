import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'
import {
  EMPTY_SETUP_TEXT,
  buildCharacterSummary,
  getCharacterMeta,
  getConceptSections,
  getWorldSections,
} from './setupPresentation'

export type SetupSummaryItem = {
  label: string
  value: string
  meta?: string[]
}

type CharacterSummaryEntry = {
  name: string
  summary: string
  meta?: string[]
}

type CharacterSummaryResult = {
  count: number
  entries: CharacterSummaryEntry[]
}

export function buildCharacterSummaryItems(characters: SetupCharacter[]): CharacterSummaryResult {
  return {
    count: characters.length,
    entries: characters.slice(0, 2).map((character) => {
      const meta = getCharacterMeta(character)

      return {
        name: character.name,
        summary: buildCharacterSummary(character),
        ...(meta.length > 0 ? { meta } : {}),
      }
    }),
  }
}

export function buildWorldSummaryItems(world: SetupWorldBuilding): SetupSummaryItem[] {
  const items = getWorldSections(world)
    .filter((section) => ['background', 'society', 'rules'].includes(section.key))
    .filter((section) => section.value !== EMPTY_SETUP_TEXT)
    .map((section) => ({
      label: section.label,
      value: section.value,
    }))

  if (items.length > 0) {
    return items
  }

  return [{ label: '世界观', value: '世界观待补充' }]
}

export function buildConceptSummaryItems(concept: SetupCoreConcept): SetupSummaryItem[] {
  const items = getConceptSections(concept)
    .filter((section) => ['theme', 'premise', 'hook'].includes(section.key))
    .filter((section) => section.value !== EMPTY_SETUP_TEXT)
    .map((section) => ({
      label: section.label,
      value: section.value,
    }))

  if (items.length > 0) {
    return items
  }

  return [{ label: '核心概念', value: '核心概念待补充' }]
}
