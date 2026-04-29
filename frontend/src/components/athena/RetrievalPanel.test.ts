// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RetrievalPanel from './RetrievalPanel.vue'

describe('RetrievalPanel', () => {
  it('groups retrieval evidence and emits creator-facing source filters', async () => {
    const wrapper = mount(RetrievalPanel, {
      props: {
        diagnostics: {
          project_id: 'project-1',
          embedding_provider: 'local',
          embedding_model: 'hash-bigram-v1',
          vector_dimension: 96,
          total_documents: 3,
          total_chunks: 4,
          total_embeddings: 4,
          documents_by_source_type: { chapter: 2, world_fact: 1 },
        },
        search: {
          query: '旧灯塔',
          total: 2,
          items: [
            {
              chunk_id: 'chunk-1',
              document_id: 'doc-1',
              source_type: 'world_fact',
              source_ref: 'claim:1',
              title: 'rule.old_lighthouse',
              chapter_index: null,
              score: 0.9,
              lexical_score: 0.8,
              vector_score: 0.7,
              snippet: '旧灯塔熄灭时，亡者不能被直接召回。',
              metadata: {},
            },
            {
              chunk_id: 'chunk-2',
              document_id: 'doc-2',
              source_type: 'chapter',
              source_ref: 'chapter:2',
              title: '第二章',
              chapter_index: 2,
              score: 0.7,
              lexical_score: 0.6,
              vector_score: 0.5,
              snippet: '林舟走进旧灯塔。',
              metadata: {},
            },
          ],
        },
        lastIndexResult: null,
        loading: false,
      },
      global: {
        stubs: {
          BaseButton: { template: '<button><slot /></button>' },
        },
      },
    })

    expect(wrapper.text()).toContain('世界事实')
    expect(wrapper.text()).toContain('章节原文')
    expect(wrapper.text()).toContain('可用于核对设定')

    await wrapper.findAll('button').find((button) => button.text().includes('世界事实'))!.trigger('click')
    await wrapper.find('input').setValue('旧灯塔')
    await wrapper.findAll('button').find((button) => button.text().includes('搜索'))!.trigger('click')

    expect(wrapper.emitted('search')?.[0]).toEqual(['旧灯塔', { source_type: 'world_fact' }])
  })
})
