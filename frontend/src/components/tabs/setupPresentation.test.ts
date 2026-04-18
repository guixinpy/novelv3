import { describe, expect, it } from 'vitest'
import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'
import {
  EMPTY_SETUP_TEXT,
  buildCharacterSummary,
  getCharacterMeta,
  getConceptSections,
  getWorldSections,
} from './setupPresentation'

describe('setup presentation', () => {
  it('getCharacterMeta 会归一化前后空白和大小写，并保留 age 0', () => {
    expect(getCharacterMeta({
      name: '零号机',
      age: 0,
      gender: ' Male ',
      character_status: ' Alive ',
    })).toEqual(['0 岁', '男', '存活'])
  })

  it('buildCharacterSummary 优先使用 background', () => {
    const character: SetupCharacter = {
      name: '林雾',
      background: '出身边陲矿镇，少年时期经历过矿难。',
      personality: '冷静克制',
      goals: '查清事故真相',
    }

    expect(buildCharacterSummary(character)).toBe('出身边陲矿镇，少年时期经历过矿难。')
  })

  it('buildCharacterSummary 在 background 为空时回退到 personality，再回退到 goals', () => {
    expect(buildCharacterSummary({
      name: '沈砚',
      background: '   ',
      personality: '偏执谨慎',
      goals: '守住最后的避难所',
    })).toBe('偏执谨慎')

    expect(buildCharacterSummary({
      name: '周岚',
      background: '',
      personality: '\n\t',
      goals: '夺回失落城区',
    })).toBe('夺回失落城区')
  })

  it('buildCharacterSummary 在三个候选都为空时返回 EMPTY_SETUP_TEXT', () => {
    expect(buildCharacterSummary({
      name: '空白角色',
      background: ' ',
      personality: '',
      goals: '   ',
    })).toBe(EMPTY_SETUP_TEXT)
  })

  it('getWorldSections 返回中文 label，并把空值归一化成待补充', () => {
    const world: SetupWorldBuilding = {
      background: '',
      geography: '群岛与雾海并存',
      society: undefined,
      rules: '  ',
      atmosphere: '旧帝国残响笼罩全境',
    }

    expect(getWorldSections(world)).toEqual([
      { key: 'background', label: '时代背景', value: '待补充' },
      { key: 'geography', label: '地理格局', value: '群岛与雾海并存' },
      { key: 'society', label: '社会结构', value: '待补充' },
      { key: 'rules', label: '规则体系', value: '待补充' },
      { key: 'atmosphere', label: '氛围基调', value: '旧帝国残响笼罩全境' },
    ])
  })

  it('getConceptSections 返回中文 label，并把空值归一化成待补充', () => {
    const concept: SetupCoreConcept = {
      premise: '死者会以植物形态复苏',
      theme: '',
      hook: '每次复苏都会泄露一段他人记忆',
      unique_selling_point: ' ',
    }

    expect(getConceptSections(concept)).toEqual([
      { key: 'theme', label: '主题', value: '待补充' },
      { key: 'premise', label: '前提设定', value: '死者会以植物形态复苏' },
      { key: 'hook', label: '核心钩子', value: '每次复苏都会泄露一段他人记忆' },
      { key: 'unique_selling_point', label: '独特卖点', value: '待补充' },
    ])
  })

  it('getCharacterMeta 格式化年龄、性别和状态，未知状态保留原值', () => {
    expect(getCharacterMeta({
      name: '陆沉',
      age: 24,
      gender: 'male',
      character_status: 'alive',
    })).toEqual(['24 岁', '男', '存活'])

    expect(getCharacterMeta({
      name: '白榆',
      age: null,
      gender: '',
      character_status: 'unknown',
    })).toEqual(['unknown'])
  })
})
