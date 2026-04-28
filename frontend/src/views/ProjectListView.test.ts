// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
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
      target_word_count: 40000,
    })
  })
})
