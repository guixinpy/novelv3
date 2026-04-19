import { describe, expect, it } from 'vitest'
import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'
import {
  buildCharacterSummaryItems,
  buildConceptSummaryItems,
  buildWorldSummaryItems,
} from './setupSummaryPresentation'

describe('setup summary presentation', () => {
  it('buildCharacterSummaryItems 返回 count 和前 2 名角色 entries', () => {
    const characters: SetupCharacter[] = [
      {
        name: '林雾',
        age: 24,
        gender: 'male',
        character_status: 'alive',
        background: '出身边陲矿镇，少年时期经历过矿难。',
        personality: '冷静克制',
        goals: '查清事故真相',
      },
      {
        name: '沈砚',
        age: 31,
        gender: 'female',
        character_status: 'dead',
        background: ' ',
        personality: '偏执谨慎',
        goals: '守住最后的避难所',
      },
      {
        name: '周岚',
        background: '夺回失落城区的流亡指挥官',
      },
    ]

    expect(buildCharacterSummaryItems(characters)).toEqual({
      count: 3,
      entries: [
        {
          name: '林雾',
          summary: '出身边陲矿镇，少年时期经历过矿难。',
          meta: ['24 岁', '男', '存活'],
        },
        {
          name: '沈砚',
          summary: '偏执谨慎',
          meta: ['31 岁', '女', '死亡'],
        },
      ],
    })
  })

  it('buildCharacterSummaryItems 在角色没有 meta 时省略 meta 字段', () => {
    const characters: SetupCharacter[] = [
      {
        name: '周岚',
        background: '夺回失落城区的流亡指挥官',
      },
    ]

    expect(buildCharacterSummaryItems(characters)).toEqual({
      count: 1,
      entries: [
        {
          name: '周岚',
          summary: '夺回失落城区的流亡指挥官',
        },
      ],
    })
  })

  it('buildCharacterSummaryItems 在空数组时返回 count 0 和空 entries', () => {
    expect(buildCharacterSummaryItems([])).toEqual({
      count: 0,
      entries: [],
    })
  })

  it('buildWorldSummaryItems 只提炼时代背景、社会结构、规则体系，空值跳过', () => {
    const world: SetupWorldBuilding = {
      background: '蒸汽帝国崩塌后的百年重建期',
      geography: '群岛与雾海并存',
      society: '城邦议会与财团共治',
      rules: '记忆税制度决定公民等级',
      atmosphere: '旧帝国残响笼罩全境',
    }

    expect(buildWorldSummaryItems(world)).toEqual([
      { label: '时代背景', value: '蒸汽帝国崩塌后的百年重建期' },
      { label: '社会结构', value: '城邦议会与财团共治' },
      { label: '规则体系', value: '记忆税制度决定公民等级' },
    ])
  })

  it('buildWorldSummaryItems 在部分目标字段为空时只保留非空项', () => {
    const world: SetupWorldBuilding = {
      background: '蒸汽帝国崩塌后的百年重建期',
      geography: '群岛与雾海并存',
      society: ' ',
      rules: '记忆税制度决定公民等级',
      atmosphere: '旧帝国残响笼罩全境',
    }

    expect(buildWorldSummaryItems(world)).toEqual([
      { label: '时代背景', value: '蒸汽帝国崩塌后的百年重建期' },
      { label: '规则体系', value: '记忆税制度决定公民等级' },
    ])
  })

  it('buildWorldSummaryItems 在目标字段全空时返回世界观待补充', () => {
    const world: SetupWorldBuilding = {
      background: ' ',
      geography: '群岛与雾海并存',
      society: '',
      rules: undefined,
      atmosphere: '旧帝国残响笼罩全境',
    }

    expect(buildWorldSummaryItems(world)).toEqual([
      { label: '世界观', value: '世界观待补充' },
    ])
  })

  it('buildConceptSummaryItems 只提炼主题、前提设定、核心钩子', () => {
    const concept: SetupCoreConcept = {
      theme: '身份与记忆的错位',
      premise: '死者会以植物形态复苏',
      hook: '每次复苏都会泄露一段他人记忆',
      unique_selling_point: '植物尸潮美学',
    }

    expect(buildConceptSummaryItems(concept)).toEqual([
      { label: '主题', value: '身份与记忆的错位' },
      { label: '前提设定', value: '死者会以植物形态复苏' },
      { label: '核心钩子', value: '每次复苏都会泄露一段他人记忆' },
    ])
  })

  it('buildConceptSummaryItems 在部分目标字段为空时只保留非空项', () => {
    const concept: SetupCoreConcept = {
      theme: '身份与记忆的错位',
      premise: ' ',
      hook: '每次复苏都会泄露一段他人记忆',
      unique_selling_point: '植物尸潮美学',
    }

    expect(buildConceptSummaryItems(concept)).toEqual([
      { label: '主题', value: '身份与记忆的错位' },
      { label: '核心钩子', value: '每次复苏都会泄露一段他人记忆' },
    ])
  })

  it('buildConceptSummaryItems 在目标字段全空时返回核心概念待补充', () => {
    const concept: SetupCoreConcept = {
      theme: '',
      premise: ' ',
      hook: undefined,
      unique_selling_point: '植物尸潮美学',
    }

    expect(buildConceptSummaryItems(concept)).toEqual([
      { label: '核心概念', value: '核心概念待补充' },
    ])
  })
})
