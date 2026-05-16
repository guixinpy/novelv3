// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import AthenaChatPanel from './AthenaChatPanel.vue'
import { useAthenaStore } from '../../stores/athena'
import { useProjectStore } from '../../stores/project'

const ModelTraceDrawerStub = defineComponent({
  name: 'ModelTraceDrawer',
  props: {
    projectId: {
      type: String,
      required: true,
    },
    traceId: {
      type: String,
      default: null,
    },
    open: {
      type: Boolean,
      required: true,
    },
  },
  template: '<div data-testid="trace-drawer" />',
})

function mountPanel(projectId = 'project-1') {
  return mount(AthenaChatPanel, {
    props: {
      open: true,
      projectId,
    },
    global: {
      stubs: {
        Teleport: true,
        Transition: false,
        ModelTraceDrawer: ModelTraceDrawerStub,
      },
    },
  })
}

function setAssistantTraceMessage(traceId: string) {
  const athena = useAthenaStore()
  athena.messages = [
    {
      id: 'athena-message-1',
      role: 'assistant',
      content: 'Athena 回复',
      trace_id: traceId,
    },
  ]
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('AthenaChatPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAthenaStore().ensureProject('project-1')
  })

  it('shows the current Athena context snapshot above historical chat messages', () => {
    const project = useProjectStore()
    const athena = useAthenaStore()
    project.currentProject = {
      id: 'project-1',
      name: '霜灯档案',
      current_word_count: 81234,
    }
    project.chapters = Array.from({ length: 20 }, (_, index) => ({
      id: `chapter-${index + 1}`,
      chapter_index: index + 1,
      title: `第${index + 1}章`,
    }))
    athena.ontology = {
      entities: {},
      relations: [],
      rules: [],
      setup_summary: null,
      profile_version: 3,
    }
    athena.retrievalDiagnostics = {
      project_id: 'project-1',
      embedding_provider: 'local',
      embedding_model: 'test',
      vector_dimension: 384,
      total_documents: 21,
      total_chunks: 130,
      total_embeddings: 130,
      total_terms: 152111,
      documents_by_source_type: {},
    }

    const wrapper = mountPanel('project-1')

    expect(wrapper.text()).toContain('当前上下文')
    expect(wrapper.text()).toContain('章节 20')
    expect(wrapper.text()).toContain('字数 81234')
    expect(wrapper.text()).toContain('Profile v3')
    expect(wrapper.text()).toContain('索引文档 21')
    expect(wrapper.text()).toContain('历史回答基于当时上下文')
  })

  it('uses the paginated chapter total instead of the loaded page length', () => {
    const project = useProjectStore()
    project.currentProject = {
      id: 'project-1',
      name: '霜灯档案',
      current_word_count: 750000,
    }
    project.chapters = Array.from({ length: 200 }, (_, index) => ({
      id: `chapter-${index + 1}`,
      chapter_index: index + 1,
      title: `第${index + 1}章`,
    }))
    project.chaptersTotal = 1000

    const wrapper = mountPanel('project-1')

    expect(wrapper.text()).toContain('章节 1000')
    expect(wrapper.text()).not.toContain('章节 200')
  })

  it('marks retrieval index metric as unread when diagnostics are not loaded', () => {
    const project = useProjectStore()
    const athena = useAthenaStore()
    project.currentProject = {
      id: 'project-1',
      name: '霜灯档案',
      current_word_count: 81234,
    }
    project.chapters = [{ id: 'chapter-1', chapter_index: 1, title: '第1章' }]
    athena.ontology = {
      entities: {},
      relations: [],
      rules: [],
      setup_summary: null,
      profile_version: 3,
    }
    athena.retrievalDiagnostics = null

    const wrapper = mountPanel('project-1')

    expect(wrapper.text()).toContain('索引文档 未读取')
    expect(wrapper.text()).not.toContain('索引文档 0')
  })

  it('shows stale longform maintenance status in the current context snapshot', () => {
    const project = useProjectStore()
    const athena = useAthenaStore()
    project.currentProject = {
      id: 'project-1',
      name: '霜灯档案',
      current_word_count: 750000,
    }
    project.chaptersTotal = 1000
    athena.longformMaintenanceDiagnostics = {
      project_id: 'project-1',
      status: 'stale',
      chapter_count: 1000,
      stale_memory_count: 2,
      missing_memory_count: 1,
      stale_retrieval_count: 3,
      missing_retrieval_count: 4,
      stale_chapter_indexes: [512, 780],
      missing_memory_chapter_indexes: [910],
      stale_retrieval_chapter_indexes: [512, 780, 910],
      missing_retrieval_chapter_indexes: [901, 902, 903, 904],
      latest_chapter_updated_at: '2026-05-16T10:00:00Z',
      latest_memory_updated_at: '2026-05-16T09:00:00Z',
      latest_retrieval_updated_at: '2026-05-16T08:00:00Z',
      latest_synced_chapter_index: 780,
    }

    const wrapper = mountPanel('project-1')

    expect(wrapper.text()).toContain('长篇记忆 待维护 10 项')
  })

  it('loads retrieval and longform diagnostics when opened with unread context', async () => {
    const athena = useAthenaStore()
    athena.loadRetrievalDiagnostics = vi.fn(async () => undefined) as typeof athena.loadRetrievalDiagnostics
    athena.loadLongformMaintenanceDiagnostics = vi.fn(async () => undefined) as typeof athena.loadLongformMaintenanceDiagnostics

    mountPanel('project-1')
    await flushPromises()

    expect(athena.loadRetrievalDiagnostics).toHaveBeenCalledWith('project-1')
    expect(athena.loadLongformMaintenanceDiagnostics).toHaveBeenCalledWith('project-1')
  })

  it('opens trace drawer with clicked Athena message trace id', async () => {
    setAssistantTraceMessage('trace-athena-1')
    const wrapper = mountPanel('project-1')

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-1',
      traceId: 'trace-athena-1',
      open: true,
    })
  })

  it('clears active trace drawer when project changes', async () => {
    setAssistantTraceMessage('trace-athena-1')
    const wrapper = mountPanel('project-1')

    await wrapper.get('[data-testid="open-trace"]').trigger('click')
    await wrapper.setProps({ projectId: 'project-2' })

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-2',
      traceId: null,
      open: false,
    })
  })
})
