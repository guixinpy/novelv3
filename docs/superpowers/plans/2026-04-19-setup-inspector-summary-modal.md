# Setup Inspector Summary Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把右侧 `设定` 面板从完整阅读区改成三张概览卡，并用一个可复用模态弹窗承接完整内容。

**Architecture:** `SetupTab.vue` 只负责右侧概览与弹窗开关，不再直接承载完整阅读内容。完整内容迁移到 `SetupDetailModal.vue`，内部复用现有 `SetupCharactersPanel.vue`、`SetupWorldPanel.vue`、`SetupConceptPanel.vue` 和 `SetupSectionTabs.vue`；通用弹窗壳层抽到 `InspectorDetailModal.vue`，便于后续别的 Inspector 内容复用。

**Tech Stack:** Vue 3 `script setup`, TypeScript, Vitest, Vue Test Utils, Vite, agent-browser

---

## File Structure

- Create: `frontend/src/components/InspectorDetailModal.vue`
  责任：通用模态弹窗壳层，处理 Teleport、遮罩、关闭按钮、Escape、内容插槽
- Create: `frontend/src/components/tabs/setupSummaryPresentation.ts`
  责任：把完整 `setup` 数据提炼为右侧概览摘要，不污染现有完整展示 helper
- Create: `frontend/src/components/tabs/setupSummaryPresentation.test.ts`
  责任：验证角色/世界观/核心概念概览提炼逻辑
- Create: `frontend/src/components/tabs/SetupSummaryCard.vue`
  责任：单张概览卡，承载标题、摘要、标签和 `查看完整`
- Create: `frontend/src/components/tabs/SetupDetailModal.vue`
  责任：`设定` 专用详情弹窗装配层，内部 tabs + 完整内容
- Modify: `frontend/src/components/tabs/SetupTab.vue`
  责任：替换右侧完整阅读内容为三张概览卡 + 弹窗状态
- Modify: `frontend/src/components/tabs/SetupTab.structured.test.ts`
  责任：从“右侧完整阅读”测试转为“右侧概览 + 弹窗”测试
- Modify: `scripts/verify_full_app_ui.sh`
  责任：browser smoke 改为校验三张概览卡、点击 `查看完整` 打开弹窗、定位到对应 section

### Task 1: 建立设定概览提炼层

**Files:**
- Create: `frontend/src/components/tabs/setupSummaryPresentation.ts`
- Create: `frontend/src/components/tabs/setupSummaryPresentation.test.ts`
- Test: `frontend/src/components/tabs/setupSummaryPresentation.test.ts`

- [ ] **Step 1: 写失败测试，锁定三张概览卡的摘要提炼规则**

```ts
import { describe, expect, it } from 'vitest'
import {
  buildCharacterSummaryItems,
  buildConceptSummaryItems,
  buildWorldSummaryItems,
} from './setupSummaryPresentation'

describe('setupSummaryPresentation', () => {
  it('角色概览提炼角色总数和前 2 名关键角色摘要', () => {
    const items = buildCharacterSummaryItems([
      {
        name: '沈砚',
        background: '旧城档案馆的修复员',
        personality: '克制',
        goals: '找回失落档案',
        age: 28,
        gender: 'male',
        character_status: 'alive',
      },
      {
        name: '周岚',
        background: '边境调查员',
        personality: '直接',
        goals: '封锁裂隙',
        age: 26,
        gender: 'female',
        character_status: 'alive',
      },
      {
        name: '顾迟',
        background: '残塔守夜人',
      },
    ])

    expect(items.count).toBe(3)
    expect(items.entries).toHaveLength(2)
    expect(items.entries[0]).toEqual({
      name: '沈砚',
      summary: '旧城档案馆的修复员',
      meta: ['28 岁', '男', '存活'],
    })
  })

  it('世界观概览优先提炼时代背景、社会结构、规则体系，空则跳过', () => {
    expect(buildWorldSummaryItems({
      background: '灾后第三纪元',
      geography: '群岛与雾海',
      society: '城邦联盟',
      rules: '记忆税制度',
      atmosphere: '',
    })).toEqual([
      { label: '时代背景', value: '灾后第三纪元' },
      { label: '社会结构', value: '城邦联盟' },
      { label: '规则体系', value: '记忆税制度' },
    ])
  })

  it('核心概念概览优先提炼主题、前提设定、核心钩子，全空时给待补充', () => {
    expect(buildConceptSummaryItems({
      theme: '',
      premise: '',
      hook: '',
      unique_selling_point: '',
    })).toEqual([
      { label: '核心概念', value: '核心概念待补充' },
    ])
  })
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupSummaryPresentation.test.ts`
Expected: FAIL，缺少 `setupSummaryPresentation.ts`。

- [ ] **Step 3: 写最小实现**

```ts
import type { SetupCharacter, SetupCoreConcept, SetupWorldBuilding } from '../../api/types'
import { buildCharacterSummary, getCharacterMeta } from './setupPresentation'

export function buildCharacterSummaryItems(characters: SetupCharacter[]) {
  return {
    count: characters.length,
    entries: characters.slice(0, 2).map((character) => ({
      name: character.name,
      summary: buildCharacterSummary(character),
      meta: getCharacterMeta(character),
    })),
  }
}

export function buildWorldSummaryItems(world: SetupWorldBuilding) {
  const items = [
    { label: '时代背景', value: world.background?.trim() || '' },
    { label: '社会结构', value: world.society?.trim() || '' },
    { label: '规则体系', value: world.rules?.trim() || '' },
  ].filter((item) => item.value)

  return items.length ? items : [{ label: '世界观', value: '世界观待补充' }]
}

export function buildConceptSummaryItems(concept: SetupCoreConcept) {
  const items = [
    { label: '主题', value: concept.theme?.trim() || '' },
    { label: '前提设定', value: concept.premise?.trim() || '' },
    { label: '核心钩子', value: concept.hook?.trim() || '' },
  ].filter((item) => item.value)

  return items.length ? items : [{ label: '核心概念', value: '核心概念待补充' }]
}
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupSummaryPresentation.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/setupSummaryPresentation.ts frontend/src/components/tabs/setupSummaryPresentation.test.ts
git commit -m "feat: add setup summary presentation helpers"
```

### Task 2: 搭建可复用详情弹窗壳层和设定详情装配

**Files:**
- Create: `frontend/src/components/InspectorDetailModal.vue`
- Create: `frontend/src/components/tabs/SetupDetailModal.vue`
- Modify: `frontend/src/components/tabs/SetupTab.structured.test.ts`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 写失败测试，锁定弹窗打开、关闭和 section 定位**

```ts
it('点击角色查看完整后打开详情弹窗并定位到角色 section', async () => {
  const wrapper = mountSetupTab()

  await wrapper.get('[data-testid="setup-summary-card-characters"] [data-testid="setup-summary-open"]').trigger('click')

  expect(wrapper.get('[data-testid="setup-detail-modal"]').exists()).toBe(true)
  expect(wrapper.get('[data-testid="setup-detail-tab-characters"]').attributes('aria-selected')).toBe('true')
  expect(wrapper.get('[data-testid="setup-detail-panel-characters"]').attributes('aria-hidden')).toBe('false')
})

it('弹窗可关闭，且不会影响右侧概览卡', async () => {
  const wrapper = mountSetupTab()

  await wrapper.get('[data-testid="setup-summary-card-world"] [data-testid="setup-summary-open"]').trigger('click')
  await wrapper.get('[data-testid="inspector-detail-modal-close"]').trigger('click')

  expect(wrapper.find('[data-testid="setup-detail-modal"]').exists()).toBe(false)
  expect(wrapper.get('[data-testid="setup-summary-card-world"]').text()).toContain('世界观')
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: FAIL，当前没有概览卡和详情弹窗。

- [ ] **Step 3: 写最小实现**

```vue
<!-- frontend/src/components/InspectorDetailModal.vue -->
<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="inspector-detail-modal"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      data-testid="setup-detail-modal"
      @click.self="$emit('close')"
    >
      <div class="inspector-detail-modal__panel">
        <header class="inspector-detail-modal__head">
          <h2 :id="titleId">{{ title }}</h2>
          <button
            type="button"
            data-testid="inspector-detail-modal-close"
            @click="$emit('close')"
          >
            ×
          </button>
        </header>
        <slot />
      </div>
    </div>
  </Teleport>
</template>
```

```vue
<!-- frontend/src/components/tabs/SetupDetailModal.vue -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SetupData } from '../../api/types'
import InspectorDetailModal from '../InspectorDetailModal.vue'
import SetupSectionTabs from './SetupSectionTabs.vue'
import SetupCharactersPanel from './SetupCharactersPanel.vue'
import SetupWorldPanel from './SetupWorldPanel.vue'
import SetupConceptPanel from './SetupConceptPanel.vue'

const props = defineProps<{
  show: boolean
  setup: SetupData
  initialSection: 'characters' | 'world' | 'concept'
}>()
</script>
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/InspectorDetailModal.vue frontend/src/components/tabs/SetupDetailModal.vue frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: add setup detail modal shell"
```

### Task 3: 把右侧设定面板替换为三张概览卡

**Files:**
- Create: `frontend/src/components/tabs/SetupSummaryCard.vue`
- Modify: `frontend/src/components/tabs/SetupTab.vue`
- Modify: `frontend/src/components/tabs/SetupTab.structured.test.ts`
- Test: `frontend/src/components/tabs/SetupTab.structured.test.ts`

- [ ] **Step 1: 写失败测试，锁定三张概览卡同时存在**

```ts
it('右侧默认同时展示角色、世界观、核心概念三张概览卡', () => {
  const wrapper = mountSetupTab()

  expect(wrapper.get('[data-testid="setup-summary-card-characters"]').text()).toContain('角色')
  expect(wrapper.get('[data-testid="setup-summary-card-world"]').text()).toContain('世界观')
  expect(wrapper.get('[data-testid="setup-summary-card-concept"]').text()).toContain('核心概念')
})

it('右侧不再直接渲染完整角色详情和字段卡', () => {
  const wrapper = mountSetupTab()

  expect(wrapper.find('[data-testid="setup-character-detail"]').exists()).toBe(false)
  expect(wrapper.find('[data-testid="setup-world-card"]').exists()).toBe(false)
  expect(wrapper.find('[data-testid="setup-concept-card"]').exists()).toBe(false)
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: FAIL，当前右侧还是完整展示。

- [ ] **Step 3: 写最小实现**

```vue
<!-- frontend/src/components/tabs/SetupSummaryCard.vue -->
<template>
  <article class="setup-summary-card" :data-testid="testId">
    <header class="setup-summary-card__head">
      <h4>{{ title }}</h4>
      <button type="button" data-testid="setup-summary-open" @click="$emit('open')">
        查看完整
      </button>
    </header>

    <div class="setup-summary-card__body">
      <slot />
    </div>
  </article>
</template>
```

```vue
<!-- frontend/src/components/tabs/SetupTab.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import SetupSummaryCard from './SetupSummaryCard.vue'
import SetupDetailModal from './SetupDetailModal.vue'
import {
  buildCharacterSummaryItems,
  buildConceptSummaryItems,
  buildWorldSummaryItems,
} from './setupSummaryPresentation'

const isDetailModalOpen = ref(false)
const detailModalSection = ref<'characters' | 'world' | 'concept'>('characters')

function openDetail(section: 'characters' | 'world' | 'concept') {
  detailModalSection.value = section
  isDetailModalOpen.value = true
}
</script>
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/tabs/SetupSummaryCard.vue frontend/src/components/tabs/SetupTab.vue frontend/src/components/tabs/SetupTab.structured.test.ts
git commit -m "feat: show setup summary cards in inspector"
```

### Task 4: 补 setup summary modal 的 browser smoke 并做全量验证

**Files:**
- Modify: `scripts/verify_full_app_ui.sh`
- Test: `scripts/verify_full_app_ui.sh`

- [ ] **Step 1: 补 browser smoke，验证概览卡和详情弹窗**

```bash
assert_eval "设定面板展示三张概览卡" "(() => {
  const ids = [
    'setup-summary-card-characters',
    'setup-summary-card-world',
    'setup-summary-card-concept',
  ]
  return ids.every((id) => Boolean(document.querySelector(`[data-testid=\"${id}\"]`)))
})()"

assert_eval "点击角色查看完整" "(() => {
  const button = document.querySelector('[data-testid=\"setup-summary-card-characters\"] [data-testid=\"setup-summary-open\"]')
  if (!button) throw new Error('未找到角色查看完整按钮')
  button.click()
  return true
})()"

wait_for_eval_true "设定详情弹窗打开并定位到角色" "(() => {
  const modal = document.querySelector('[data-testid=\"setup-detail-modal\"]')
  const tab = document.querySelector('[data-testid=\"setup-detail-tab-characters\"]')
  return Boolean(modal) && tab?.getAttribute('aria-selected') === 'true'
})()"
```

- [ ] **Step 2: 跑定向前端单测**

Run: `cd frontend && npm run test:unit -- src/components/tabs/setupSummaryPresentation.test.ts src/components/tabs/SetupTab.structured.test.ts`
Expected: PASS

- [ ] **Step 3: 跑构建**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 4: 跑完整 UI 验证**

Run: `./scripts/verify_full_app_ui.sh`
Expected: PASS，setup summary modal smoke 通过，browser errors / console errors 为 0

- [ ] **Step 5: 提交**

```bash
git add scripts/verify_full_app_ui.sh
git commit -m "test: cover setup summary modal smoke"
```

## Self-Review

### Spec Coverage

- 三张概览卡：Task 1, Task 3
- 复用模态弹窗：Task 2
- 弹窗内部三类完整内容：Task 2
- 右侧只保留概览：Task 3
- 详情入口定位到对应 section：Task 2, Task 4
- 回归脚本覆盖：Task 4

### Placeholder Scan

- 未使用 `TODO / TBD / implement later`
- 每个任务都有具体文件、测试、命令和代码片段
- 没有“类似 Task N”这种偷懒描述

### Type Consistency

- section id 统一为 `'characters' | 'world' | 'concept'`
- 右侧状态统一使用 `detailModalSection + isDetailModalOpen`
- 完整内容继续复用现有 `SetupCharactersPanel / SetupWorldPanel / SetupConceptPanel`
