// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from './BaseModal.vue'

describe('BaseModal', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    document.body.style.overflow = ''
  })

  it('初始 open=true 时锁定 body 滚动并聚焦弹窗', async () => {
    const wrapper = mount(BaseModal, {
      props: {
        open: true,
        title: '测试弹窗',
        width: '760px',
      },
      attachTo: document.body,
    })

    await wrapper.vm.$nextTick()

    const panel = document.body.querySelector<HTMLElement>('.base-modal__panel')
    expect(document.body.style.overflow).toBe('hidden')
    expect(panel).not.toBeNull()
    expect(document.activeElement).toBe(panel)

    wrapper.unmount()
  })
})
