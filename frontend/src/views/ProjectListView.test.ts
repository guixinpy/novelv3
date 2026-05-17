// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectListView from './ProjectListView.vue'
import { api } from '../api/client'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/client', () => ({
  api: {
    listProjects: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}))

describe('ProjectListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.listProjects).mockResolvedValue([])
    vi.mocked(api.createProject).mockResolvedValue({
      id: 'project-1',
      name: '雾港二十夜',
      genre: '都市奇幻悬疑',
      current_word_count: 0,
      status: 'draft',
      updated_at: new Date().toISOString(),
    })
    vi.mocked(api.updateProject).mockResolvedValue({
      id: 'project-1',
      name: '雾港二十夜',
      genre: '都市奇幻悬疑',
      current_word_count: 0,
      status: 'draft',
      ai_model: 'deepseek-reasoner',
      updated_at: new Date().toISOString(),
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('treats backend UTC timestamps without timezone as current time', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-28T08:00:30Z'))
    vi.mocked(api.listProjects).mockResolvedValue([
      {
        id: 'project-1',
        name: '雾港二十夜',
        genre: '都市奇幻悬疑',
        current_word_count: 0,
        status: 'draft',
        updated_at: '2026-04-28T08:00:00.000000',
      },
    ])

    const wrapper = mount(ProjectListView)
    await Promise.resolve()
    await nextTick()

    expect(wrapper.text()).toContain('刚刚')
  })

  it('sends target word count when creating a project', async () => {
    const wrapper = mount(ProjectListView, { attachTo: document.body })
    await Promise.resolve()

    const newProjectButton = wrapper.findAll('button').find((button) => button.text() === '新建项目')
    expect(newProjectButton).toBeTruthy()
    await newProjectButton!.trigger('click')
    await nextTick()
    const inputs = Array.from(document.querySelectorAll('input'))
    expect(inputs).toHaveLength(4)
    await wrapper.findAllComponents({ name: 'BaseInput' })[0].vm.$emit('update:modelValue', '雾港二十夜')
    await wrapper.findAllComponents({ name: 'BaseInput' })[1].vm.$emit('update:modelValue', '都市奇幻悬疑')
    await wrapper.findAllComponents({ name: 'BaseInput' })[2].vm.$emit('update:modelValue', '20')
    await wrapper.findAllComponents({ name: 'BaseInput' })[3].vm.$emit('update:modelValue', '40000')
    await nextTick()

    const createButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.trim() === '创建')
    expect(createButton).toBeTruthy()
    createButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()

    expect(api.createProject).toHaveBeenCalledWith({
      name: '雾港二十夜',
      genre: '都市奇幻悬疑',
      target_chapter_count: 20,
      target_word_count: 40000,
      ai_model: 'deepseek-chat',
    })
  })

  it('sends selected AI model when creating a project', async () => {
    const wrapper = mount(ProjectListView, { attachTo: document.body })
    await Promise.resolve()

    await wrapper.get('[data-testid="project-create-button"]').trigger('click')
    await nextTick()
    await wrapper.findAllComponents({ name: 'BaseInput' })[0].vm.$emit('update:modelValue', '推理模型长篇')
    const modelSelect = document.querySelector('[data-testid="project-ai-model-select"]') as HTMLSelectElement
    expect(modelSelect).toBeTruthy()
    modelSelect.value = 'deepseek-reasoner'
    modelSelect.dispatchEvent(new Event('change', { bubbles: true }))
    await nextTick()

    const createButton = document.querySelector('[data-testid="project-create-submit"]')
    expect(createButton).toBeTruthy()
    createButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()

    expect(api.createProject).toHaveBeenCalledWith({
      name: '推理模型长篇',
      ai_model: 'deepseek-reasoner',
    })
  })

  it('updates a project AI model from the list row', async () => {
    vi.mocked(api.listProjects).mockResolvedValue([
      {
        id: 'project-1',
        name: '雾港二十夜',
        genre: '都市奇幻悬疑',
        current_word_count: 0,
        status: 'draft',
        ai_model: 'deepseek-chat',
        updated_at: '2026-04-28T08:00:00.000000',
      },
    ])
    const wrapper = mount(ProjectListView)
    await flushPromises()
    await nextTick()

    const modelSelect = wrapper.get('[data-testid="project-row-ai-model-project-1"]')
    await modelSelect.setValue('deepseek-reasoner')

    expect(api.updateProject).toHaveBeenCalledWith('project-1', { ai_model: 'deepseek-reasoner' })
  })

  it('closes the create modal after creating a project successfully', async () => {
    const wrapper = mount(ProjectListView, { attachTo: document.body })
    await Promise.resolve()

    await wrapper.get('[data-testid="project-create-button"]').trigger('click')
    await nextTick()
    await wrapper.findAllComponents({ name: 'BaseInput' })[0].vm.$emit('update:modelValue', '雾港二十夜')
    await nextTick()

    const createButton = document.querySelector('[data-testid="project-create-submit"]')
    expect(createButton).toBeTruthy()
    createButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()
    await flushPromises()
    await nextTick()

    expect(document.querySelector('[data-testid="project-create-modal"]')).toBeNull()
  })

  it('exposes stable selectors for e2e project creation', async () => {
    const wrapper = mount(ProjectListView, { attachTo: document.body })
    await Promise.resolve()

    expect(wrapper.find('[data-testid="project-create-button"]').exists()).toBe(true)
    await wrapper.get('[data-testid="project-create-button"]').trigger('click')
    await nextTick()

    expect(document.querySelector('[data-testid="project-create-modal"]')).toBeTruthy()
    expect(document.querySelector('[data-testid="project-name-input"] input')).toBeTruthy()
    expect(document.querySelector('[data-testid="project-create-submit"]')).toBeTruthy()
  })
})
