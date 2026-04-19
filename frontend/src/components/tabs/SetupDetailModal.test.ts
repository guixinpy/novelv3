// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { SetupData } from '../../api/types'
import SetupDetailModal from './SetupDetailModal.vue'

const mountedWrappers: VueWrapper[] = []

const setupFixture: SetupData = {
  id: 'setup-1',
  project_id: 'project-1',
  status: 'ready',
  created_at: '2026-04-18T00:00:00Z',
  updated_at: '2026-04-18T00:00:00Z',
  characters: [
    {
      name: '沈砚',
      background: '旧城档案馆的修复员。',
      personality: '冷静克制，但对真相近乎偏执。',
      goals: '查清师父失踪与记忆税黑市的关联。',
      age: 28,
      gender: 'male',
      character_status: 'alive',
    },
  ],
  world_building: {
    background: '灾后第三纪元，旧城废墟与档案机关并存。',
    geography: '新陆与浮岛群',
    society: '档案机关垄断记忆修复，民间巡夜人维持边境秩序。',
    rules: '记忆碎片可以被交易，但篡改会引发城市级回响。',
    atmosphere: '潮湿、肃静、带着持续失真的钟声。',
  },
  core_concept: {
    theme: '记忆决定身份，篡改记忆是否等于篡改人生。',
    premise: '记忆可被征税和交易',
    hook: '主角修复的档案会反过来改写现实。',
    unique_selling_point: '档案修复决定现实。',
  },
}

function mountSetupDetailModal(initialSection: 'characters' | 'world' | 'concept' = 'characters') {
  const wrapper = mount(SetupDetailModal, {
    attachTo: document.body,
    props: {
      show: true,
      setup: setupFixture,
      initialSection,
    },
  })

  mountedWrappers.push(wrapper)
  return wrapper
}

afterEach(() => {
  while (mountedWrappers.length) {
    mountedWrappers.pop()?.unmount()
  }
  document.body.innerHTML = ''
})

describe('SetupDetailModal', () => {
  it('show=true 时会通过真实 modal 渲染到 document.body', async () => {
    mountSetupDetailModal()
    await nextTick()

    const modal = document.body.querySelector('[data-testid="setup-detail-modal"]')
    expect(modal).not.toBeNull()
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()
  })

  it('initialSection=world 时激活真实 world panel，并选中 world tab', async () => {
    mountSetupDetailModal('world')
    await nextTick()

    const panel = document.body.querySelector('[data-testid="setup-detail-panel-world"]')
    const tab = document.body.querySelector('[data-testid="setup-detail-tab-world"]')
    const charactersPanel = document.body.querySelector('[data-testid="setup-detail-panel-characters"]')
    const conceptPanel = document.body.querySelector('[data-testid="setup-detail-panel-concept"]')

    expect(panel?.getAttribute('aria-hidden')).toBe('false')
    expect(panel?.hasAttribute('hidden')).toBe(false)
    expect(tab?.getAttribute('aria-selected')).toBe('true')
    expect((charactersPanel as HTMLElement | null)?.style.display).toBe('none')
    expect((conceptPanel as HTMLElement | null)?.style.display).toBe('none')
  })

  it('切换到 concept 时会激活真实 concept panel', async () => {
    mountSetupDetailModal('world')
    await nextTick()

    const conceptTab = document.body.querySelector('[data-testid="setup-detail-tab-concept"]')
    if (!(conceptTab instanceof HTMLButtonElement)) {
      throw new Error('未找到核心概念 tab')
    }

    conceptTab.click()
    await nextTick()

    const worldPanel = document.body.querySelector('[data-testid="setup-detail-panel-world"]')
    const conceptPanel = document.body.querySelector('[data-testid="setup-detail-panel-concept"]')

    expect(worldPanel?.getAttribute('aria-hidden')).toBe('true')
    expect(conceptPanel?.getAttribute('aria-hidden')).toBe('false')
    expect(conceptPanel?.hasAttribute('hidden')).toBe(false)
    expect((worldPanel as HTMLElement | null)?.style.display).toBe('none')
    expect((conceptPanel as HTMLElement | null)?.style.display).toBe('')
  })

  it('点击关闭按钮或按 Escape 会发出 close 事件', async () => {
    const wrapper = mountSetupDetailModal()
    await nextTick()

    const closeButton = document.body.querySelector('[data-testid="inspector-detail-modal-close"]')
    if (!(closeButton instanceof HTMLButtonElement)) {
      throw new Error('未找到关闭按钮')
    }

    closeButton.click()
    await nextTick()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()

    expect(wrapper.emitted('close')).toHaveLength(2)
  })

  it('世界观面板确实渲染 5 张字段卡，且标签和值正确', async () => {
    mountSetupDetailModal('world')
    await nextTick()

    const panel = document.body.querySelector('[data-testid="setup-detail-panel-world"]')
    if (!(panel instanceof HTMLElement)) {
      throw new Error('未找到世界观面板')
    }

    const cards = Array.from(panel.querySelectorAll('[data-testid="setup-world-card"]'))
    const pairs = cards.map((card) => ({
      label: card.querySelector('[data-testid="setup-world-label"]')?.textContent?.trim(),
      value: card.querySelector('[data-testid="setup-world-value"]')?.textContent?.trim(),
    }))

    expect(cards).toHaveLength(5)
    expect(pairs).toEqual([
      { label: '时代背景', value: '灾后第三纪元，旧城废墟与档案机关并存。' },
      { label: '地理格局', value: '新陆与浮岛群' },
      { label: '社会结构', value: '档案机关垄断记忆修复，民间巡夜人维持边境秩序。' },
      { label: '规则体系', value: '记忆碎片可以被交易，但篡改会引发城市级回响。' },
      { label: '氛围基调', value: '潮湿、肃静、带着持续失真的钟声。' },
    ])
  })

  it('核心概念面板确实渲染 4 张字段卡，且标签和值正确', async () => {
    mountSetupDetailModal('concept')
    await nextTick()

    const panel = document.body.querySelector('[data-testid="setup-detail-panel-concept"]')
    if (!(panel instanceof HTMLElement)) {
      throw new Error('未找到核心概念面板')
    }

    const cards = Array.from(panel.querySelectorAll('[data-testid="setup-concept-card"]'))
    const pairs = cards.map((card) => ({
      label: card.querySelector('[data-testid="setup-concept-label"]')?.textContent?.trim(),
      value: card.querySelector('[data-testid="setup-concept-value"]')?.textContent?.trim(),
    }))

    expect(cards).toHaveLength(4)
    expect(pairs).toEqual([
      { label: '主题', value: '记忆决定身份，篡改记忆是否等于篡改人生。' },
      { label: '前提设定', value: '记忆可被征税和交易' },
      { label: '核心钩子', value: '主角修复的档案会反过来改写现实。' },
      { label: '独特卖点', value: '档案修复决定现实。' },
    ])
  })
})
