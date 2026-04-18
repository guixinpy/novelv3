# Setup Inspector Structured View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把右侧 Inspector 的 `设定` 面板改成带二级 tabs 的结构化视图，让角色、世界观、核心概念都能清晰展示并支持后续精准更新。

**Architecture:** 保持 Inspector 顶层 `设定` 入口不变，在 `SetupTab` 内部引入 `角色 / 世界观 / 核心概念` 二级 tabs。前端基于已有后端 `setup` schema 做展示归一化，并拆出专用子组件处理角色主从视图、世界观字段卡和核心概念字段卡，避免继续在 `SetupTab.vue` 堆模板和 `any`。

**Tech Stack:** Vue 3 `script setup`, TypeScript, Vitest, Vue Test Utils, Vite, agent-browser

---

## File Structure

- Modify: `frontend/src/api/types.ts`
  责任：补齐 `SetupData / SetupCharacter / SetupWorldBuilding / SetupCoreConcept` 前端类型
- Create: `frontend/src/components/tabs/setupPresentation.ts`
  责任：字段标题映射、空值归一化、角色摘要提取、元信息格式化
- Create: `frontend/src/components/tabs/setupPresentation.test.ts`
  责任：覆盖展示归一化逻辑，防止回退为黑盒字符串
- Create: `frontend/src/components/tabs/SetupSectionTabs.vue`
  责任：`角色 / 世界观 / 核心概念` 二级 tabs 切换条
- Create: `frontend/src/components/tabs/SetupCharactersPanel.vue`
  责任：角色列表 + 当前角色详情
- Create: `frontend/src/components/tabs/SetupWorldPanel.vue`
  责任：世界观字段卡片展示
- Create: `frontend/src/components/tabs/SetupConceptPanel.vue`
  责任：核心概念字段卡片展示
- Modify: `frontend/src/components/tabs/SetupTab.vue`
  责任：设定面板壳层、二级 tabs 状态、子组件装配、项目切换时重置子视图状态
- Create: `frontend/src/components/tabs/SetupTab.structured.test.ts`
  责任：覆盖默认二级 tab、角色切换、空字段占位、去 JSON dump

### Task 1: 建立设定类型与展示归一化层

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/components/tabs/setupPresentation.ts`
- Test: `frontend/src/components/tabs/setupPresentation.test.ts`

- [ ] **Step 1: 写失败测试，锁定角色摘要、空值占位和字段映射**

```ts
import { describe, expect, it } from 'vitest'
import {
  EMPTY_SETUP_TEXT,
  buildCharacterSummary,
  getCharacterMeta,
  getConceptSections,
  getWorldSections,
} from './setupPresentation'

describe('setupPresentation', () => {
  it('优先用背景生成角色摘要，缺失时回退到性格和目标', () => {
    expect(buildCharacterSummary({
      name: '凯尔',
      background: '火星殖民地工程师',
      personality: '理想主义',
      goals: '追查父亲死因',
    })).toBe('火星殖民地工程师')

    expect(buildCharacterSummary({
      name: '莉娜',
      background: '',
      personality: '理性至上',
      goals: '阻止军事化',
    })).toBe('理性至上')

    expect(buildCharacterSummary({
      name: '艾娃',
      background: '',
      personality: '',
      goals: '',
    })).toBe(EMPTY_SETUP_TEXT)
  })

  it('世界观和核心概念字段会被映射为中文标题和占位文本', () => {
    expect(getWorldSections({
      background: '战争后的脆弱和平',
      geography: '',
      society: '三阶层撕裂',
      rules: '',
      atmosphere: '希望与危机并存',
    })).toEqual([
      { key: 'background', label: '时代背景', value: '战争后的脆弱和平' },
      { key: 'geography', label: '地理格局', value: EMPTY_SETUP_TEXT },
      { key: 'society', label: '社会结构', value: '三阶层撕裂' },
      { key: 'rules', label: '规则体系', value: EMPTY_SETUP_TEXT },
      { key: 'atmosphere', label: '氛围基调', value: '希望与危机并存' },
    ])

    expect(getConceptSections({
      theme: '',
      premise: '星火改变权力平衡',
      hook: '',
      unique_selling_point: '硬科幻 + 政治惊悚',
    })[0]).toEqual({
      key: 'theme',
      label: '主题',
      value: EMPTY_SETUP_TEXT,
    })
  })

  it('角色元信息会按年龄 / 性别 / 状态输出可读标签', () => {
    expect(getCharacterMeta({
      name: '凯尔',
      age: 24,
      gender: '男',
      character_status: 'alive',
    })).toEqual(['24 岁', '男', '存活'])

    expect(getCharacterMeta({
      name: '艾娃',
      age: null,
      gender: '',
      character_status: 'unknown',
    })).toEqual(['unknown'])
  })
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupPresentation.test.ts`
Expected: FAIL，缺少 `setupPresentation.ts` 和相关导出。

- [ ] **Step 3: 写最小实现，补类型和展示函数**

```ts
// frontend/src/api/types.ts
export interface SetupCharacter {
  name: string
  age?: number | null
  gender?: string | null
  personality?: string | null
  background?: string | null
  goals?: string | null
  character_status?: string | null
}

export interface SetupWorldBuilding {
  background?: string | null
  geography?: string | null
  society?: string | null
  rules?: string | null
  atmosphere?: string | null
}

export interface SetupCoreConcept {
  theme?: string | null
  premise?: string | null
  hook?: string | null
  unique_selling_point?: string | null
}

export interface SetupData {
  id: string
  project_id: string
  world_building: SetupWorldBuilding
  characters: SetupCharacter[]
  core_concept: SetupCoreConcept
  status: string
  created_at: string
  updated_at: string
}
```

```ts
// frontend/src/components/tabs/setupPresentation.ts
import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'

export const EMPTY_SETUP_TEXT = '待补充'

type SectionDescriptor<T extends string> = {
  key: T
  label: string
  value: string
}

function normalizeText(value: unknown) {
  if (typeof value !== 'string') return EMPTY_SETUP_TEXT
  const trimmed = value.trim()
  return trimmed || EMPTY_SETUP_TEXT
}

export function buildCharacterSummary(character: SetupCharacter) {
  const summaryCandidates = [
    normalizeText(character.background),
    normalizeText(character.personality),
    normalizeText(character.goals),
  ]
  return summaryCandidates.find((value) => value !== EMPTY_SETUP_TEXT) ?? EMPTY_SETUP_TEXT
}

export function getCharacterMeta(character: SetupCharacter) {
  const items: string[] = []
  if (typeof character.age === 'number' && character.age > 0) items.push(`${character.age} 岁`)
  const gender = normalizeText(character.gender)
  if (gender !== EMPTY_SETUP_TEXT) items.push(gender)
  const status = normalizeText(character.character_status)
  if (status !== EMPTY_SETUP_TEXT) items.push(status === 'alive' ? '存活' : status)
  return items.length ? items : [EMPTY_SETUP_TEXT]
}

export function getWorldSections(world: SetupWorldBuilding): SectionDescriptor<keyof SetupWorldBuilding>[] {
  return [
    { key: 'background', label: '时代背景', value: normalizeText(world.background) },
    { key: 'geography', label: '地理格局', value: normalizeText(world.geography) },
    { key: 'society', label: '社会结构', value: normalizeText(world.society) },
    { key: 'rules', label: '规则体系', value: normalizeText(world.rules) },
    { key: 'atmosphere', label: '氛围基调', value: normalizeText(world.atmosphere) },
  ]
}

export function getConceptSections(concept: SetupCoreConcept): SectionDescriptor<keyof SetupCoreConcept>[] {
  return [
    { key: 'theme', label: '主题', value: normalizeText(concept.theme) },
    { key: 'premise', label: '前提设定', value: normalizeText(concept.premise) },
    { key: 'hook', label: '核心钩子', value: normalizeText(concept.hook) },
    { key: 'unique_selling_point', label: '独特卖点', value: normalizeText(concept.unique_selling_point) },
  ]
}
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupPresentation.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api/types.ts frontend/src/components/tabs/setupPresentation.ts frontend/src/components/tabs/setupPresentation.test.ts
git commit -m "feat: add setup presentation helpers"
```

### Task 2: 搭建设定面板壳层与二级 tabs

**Files:**
- Create: `frontend/src/components/tabs/SetupSectionTabs.vue`
- Modify: `frontend/src/components/tabs/SetupTab.vue`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 写失败测试，锁定默认停在“角色”并支持切换二级 tabs**

```ts
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SetupTab from './SetupTab.vue'

const setupFixture = {
  id: 'setup-1',
  project_id: 'project-1',
  status: 'generated',
  created_at: '2026-04-18T00:00:00Z',
  updated_at: '2026-04-18T00:00:00Z',
  characters: [{ name: '凯尔', background: '火星殖民地工程师' }],
  world_building: { background: '星火战争后的和平', geography: '', society: '', rules: '', atmosphere: '' },
  core_concept: { theme: '自由与责任', premise: '', hook: '', unique_selling_point: '' },
}

describe('SetupTab structured view', () => {
  it('默认显示角色子视图，可切到世界观和核心概念', async () => {
    const wrapper = mount(SetupTab, { props: { setup: setupFixture } })

    expect(wrapper.text()).toContain('角色')
    expect(wrapper.text()).toContain('凯尔')
    expect(wrapper.text()).not.toContain('时代背景')

    await wrapper.get('[data-testid="setup-section-tab-world"]').trigger('click')
    expect(wrapper.text()).toContain('时代背景')
    expect(wrapper.text()).not.toContain('凯尔')

    await wrapper.get('[data-testid="setup-section-tab-concept"]').trigger('click')
    expect(wrapper.text()).toContain('主题')
    expect(wrapper.text()).toContain('自由与责任')
  })
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: FAIL，当前 `SetupTab.vue` 既没有二级 tabs，也没有对应的 `data-testid`。

- [ ] **Step 3: 写最小实现，搭建壳层和二级 tabs 状态**

```vue
<!-- frontend/src/components/tabs/SetupSectionTabs.vue -->
<template>
  <div class="setup-section-tabs" data-testid="setup-section-tabs">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="setup-section-tabs__button"
      :class="{ 'is-active': item.id === active }"
      :data-testid="`setup-section-tab-${item.id}`"
      @click="$emit('select', item.id)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  active: 'characters' | 'world' | 'concept'
  items: { id: 'characters' | 'world' | 'concept'; label: string }[]
}>()

defineEmits<{ select: [id: 'characters' | 'world' | 'concept'] }>()
</script>
```

```vue
<!-- frontend/src/components/tabs/SetupTab.vue -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SetupData } from '../../api/types'
import SetupSectionTabs from './SetupSectionTabs.vue'

const props = defineProps<{ setup: SetupData | null }>()

const activeSection = ref<'characters' | 'world' | 'concept'>('characters')

const sectionItems = [
  { id: 'characters', label: '角色' },
  { id: 'world', label: '世界观' },
  { id: 'concept', label: '核心概念' },
] as const

watch(() => props.setup?.id, () => {
  activeSection.value = 'characters'
})
</script>
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/SetupSectionTabs.vue frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: add structured setup section tabs"
```

### Task 3: 实现角色主从视图

**Files:**
- Create: `frontend/src/components/tabs/SetupCharactersPanel.vue`
- Modify: `frontend/src/components/tabs/SetupTab.vue`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 写失败测试，锁定角色列表切换详情与空字段占位**

```ts
it('点击角色列表后详情区切换，空字段显示待补充', async () => {
  const wrapper = mount(SetupTab, {
    props: {
      setup: {
        ...setupFixture,
        characters: [
          { name: '凯尔', age: 24, gender: '男', background: '工程师', personality: '理想主义', goals: '追查真相', character_status: 'alive' },
          { name: '艾娃', age: null, gender: '', background: '', personality: '', goals: '', character_status: 'alive' },
        ],
      },
    },
  })

  expect(wrapper.get('[data-testid="setup-character-detail"]').text()).toContain('凯尔')
  expect(wrapper.get('[data-testid="setup-character-detail"]').text()).toContain('理想主义')

  await wrapper.get('[data-testid="setup-character-item-艾娃"]').trigger('click')

  const detail = wrapper.get('[data-testid="setup-character-detail"]').text()
  expect(detail).toContain('艾娃')
  expect(detail).toContain('待补充')
  expect(detail).toContain('存活')
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: FAIL，当前没有角色主从视图，也没有详情卡。

- [ ] **Step 3: 写最小实现，补角色列表与详情卡**

```vue
<!-- frontend/src/components/tabs/SetupCharactersPanel.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { SetupCharacter } from '../../api/types'
import { EMPTY_SETUP_TEXT, buildCharacterSummary, getCharacterMeta } from './setupPresentation'

const props = defineProps<{
  characters: SetupCharacter[]
  activeCharacterName: string | null
}>()

const emit = defineEmits<{ select: [name: string] }>()

const activeCharacter = computed(() =>
  props.characters.find((character) => character.name === props.activeCharacterName) ?? props.characters[0] ?? null,
)
</script>

<template>
  <div class="setup-characters">
    <aside class="setup-characters__list">
      <button
        v-for="character in characters"
        :key="character.name"
        type="button"
        :data-testid="`setup-character-item-${character.name}`"
        @click="emit('select', character.name)"
      >
        {{ character.name }}
        {{ buildCharacterSummary(character) }}
      </button>
    </aside>

    <section v-if="activeCharacter" class="setup-characters__detail" data-testid="setup-character-detail">
      <h4>{{ activeCharacter.name }}</h4>
      <p>{{ getCharacterMeta(activeCharacter).join(' · ') }}</p>
      <p>{{ activeCharacter.personality?.trim() || EMPTY_SETUP_TEXT }}</p>
      <p>{{ activeCharacter.background?.trim() || EMPTY_SETUP_TEXT }}</p>
      <p>{{ activeCharacter.goals?.trim() || EMPTY_SETUP_TEXT }}</p>
    </section>
  </div>
</template>
```

```vue
<!-- frontend/src/components/tabs/SetupTab.vue -->
<script setup lang="ts">
const activeCharacterName = ref<string | null>(null)

watch(() => props.setup?.id, () => {
  activeSection.value = 'characters'
  activeCharacterName.value = props.setup?.characters?.[0]?.name ?? null
}, { immediate: true })

watch(() => props.setup?.characters, (nextCharacters) => {
  const names = new Set((nextCharacters || []).map((character) => character.name))
  if (!activeCharacterName.value || !names.has(activeCharacterName.value)) {
    activeCharacterName.value = nextCharacters?.[0]?.name ?? null
  }
}, { deep: true })
</script>
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/SetupCharactersPanel.vue frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: add setup character master detail panel"
```

### Task 4: 实现世界观与核心概念字段卡

**Files:**
- Create: `frontend/src/components/tabs/SetupWorldPanel.vue`
- Create: `frontend/src/components/tabs/SetupConceptPanel.vue`
- Modify: `frontend/src/components/tabs/SetupTab.vue`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 写失败测试，锁定字段卡展示并禁止 JSON dump**

```ts
it('世界观和核心概念以字段卡展示，不再输出 JSON 字符串', async () => {
  const wrapper = mount(SetupTab, { props: { setup: setupFixture } })

  await wrapper.get('[data-testid="setup-section-tab-world"]').trigger('click')
  const worldText = wrapper.text()
  expect(worldText).toContain('时代背景')
  expect(worldText).toContain('星火战争后的和平')
  expect(worldText).not.toContain('"background"')
  expect(worldText).toContain('待补充')

  await wrapper.get('[data-testid="setup-section-tab-concept"]').trigger('click')
  const conceptText = wrapper.text()
  expect(conceptText).toContain('主题')
  expect(conceptText).toContain('自由与责任')
  expect(conceptText).not.toContain('"theme"')
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: FAIL，当前还没有字段卡子组件。

- [ ] **Step 3: 写最小实现，补世界观与核心概念面板**

```vue
<!-- frontend/src/components/tabs/SetupWorldPanel.vue -->
<script setup lang="ts">
import type { SetupWorldBuilding } from '../../api/types'
import { getWorldSections } from './setupPresentation'

const props = defineProps<{ world: SetupWorldBuilding }>()
</script>

<template>
  <div class="setup-grid">
    <article v-for="section in getWorldSections(world)" :key="section.key" class="setup-field-card">
      <p class="setup-field-card__label">{{ section.label }}</p>
      <p class="setup-field-card__value">{{ section.value }}</p>
    </article>
  </div>
</template>
```

```vue
<!-- frontend/src/components/tabs/SetupConceptPanel.vue -->
<script setup lang="ts">
import type { SetupCoreConcept } from '../../api/types'
import { getConceptSections } from './setupPresentation'

const props = defineProps<{ concept: SetupCoreConcept }>()
</script>

<template>
  <div class="setup-grid">
    <article v-for="section in getConceptSections(concept)" :key="section.key" class="setup-field-card">
      <p class="setup-field-card__label">{{ section.label }}</p>
      <p class="setup-field-card__value">{{ section.value }}</p>
    </article>
  </div>
</template>
```

- [ ] **Step 4: 跑目标测试和相关单测**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupPresentation.test.ts src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/SetupWorldPanel.vue frontend/src/components/tabs/SetupConceptPanel.vue frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: render setup world and concept panels"
```

### Task 5: 全量验证与浏览器回归

**Files:**
- Modify: `frontend/src/components/tabs/SetupTab.vue`
- Modify: `frontend/src/components/tabs/SetupSectionTabs.vue`
- Modify: `frontend/src/components/tabs/SetupCharactersPanel.vue`
- Modify: `frontend/src/components/tabs/SetupWorldPanel.vue`
- Modify: `frontend/src/components/tabs/SetupConceptPanel.vue`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 跑全量前端单测**

Run: `cd frontend && npm run test:unit`
Expected: PASS

- [ ] **Step 2: 跑构建**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: 用浏览器回归设定面板真实效果**

Run:

```bash
agent-browser open http://127.0.0.1:8000/projects/5b95b442-724b-4187-9507-283bf709dffa
agent-browser wait --text "设定"
agent-browser find role button click --name "设定"
agent-browser wait --text "角色"
agent-browser click "[data-testid='setup-section-tab-world']"
agent-browser wait --text "时代背景"
agent-browser click "[data-testid='setup-section-tab-concept']"
agent-browser wait --text "主题"
```

Expected:

- `设定` 面板默认进入 `角色`
- 角色列表存在，点击可切换详情
- `世界观` / `核心概念` 不再出现 JSON key 文本

- [ ] **Step 4: 跑完整 UI 回归脚本**

Run: `./scripts/verify_full_app_ui.sh`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupSectionTabs.vue frontend/src/components/tabs/SetupCharactersPanel.vue frontend/src/components/tabs/SetupWorldPanel.vue frontend/src/components/tabs/SetupConceptPanel.vue frontend/src/components/tabs/setupPresentation.ts frontend/src/components/tabs/setupPresentation.test.ts frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: restructure setup inspector panel"
```

## Self-Review

### Spec Coverage

- 二级 tabs：Task 2
- 角色列表 + 详情：Task 3
- 世界观字段卡：Task 4
- 核心概念字段卡：Task 4
- 空字段 `待补充`：Task 1, Task 3, Task 4
- 类型收紧：Task 1
- 浏览器验证：Task 5

### Placeholder Scan

- 未使用 `TODO / TBD / implement later`
- 每个代码步骤都包含了具体文件和示例代码
- 每个测试步骤都给了明确命令和预期结果

### Type Consistency

- 二级 tab id 统一使用 `'characters' | 'world' | 'concept'`
- 设定数据类型统一使用 `SetupData / SetupCharacter / SetupWorldBuilding / SetupCoreConcept`
- 展示 helper 统一由 `setupPresentation.ts` 提供，避免模板里重复兜底
