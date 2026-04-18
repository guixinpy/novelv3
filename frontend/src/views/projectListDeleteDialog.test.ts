import { describe, expect, it, vi } from 'vitest'
import type { ProjectListProject } from '../components/list/projectListMeta'
import { createProjectDeleteDialog } from './projectListDeleteDialog'

const project: ProjectListProject = {
  id: 'project-1',
  name: '植化尸潮',
  genre: '科幻',
  current_phase: 'outline',
  status: 'outline_generated',
}

describe('project list delete dialog', () => {
  it('open() 会把待删项目提升到列表页状态，close() 会收起弹窗', () => {
    const dialog = createProjectDeleteDialog()

    dialog.open(project)
    expect(dialog.isOpen.value).toBe(true)
    expect(dialog.targetProject.value).toEqual(project)

    dialog.close()
    expect(dialog.isOpen.value).toBe(false)
    expect(dialog.targetProject.value).toBe(null)
  })

  it('confirm() 成功后会调用删除器并清空弹窗状态', async () => {
    const dialog = createProjectDeleteDialog()
    const removeProject = vi.fn().mockResolvedValue(undefined)

    dialog.open(project)
    const result = await dialog.confirm(removeProject)

    expect(result).toBe(true)
    expect(removeProject).toHaveBeenCalledWith('project-1')
    expect(dialog.isOpen.value).toBe(false)
    expect(dialog.targetProject.value).toBe(null)
    expect(dialog.deletingProjectId.value).toBe(null)
    expect(dialog.errorMessage.value).toBe('')
  })

  it('confirm() 失败后会保留弹窗并暴露错误文案，避免用户失去上下文', async () => {
    const dialog = createProjectDeleteDialog()
    const removeProject = vi.fn().mockRejectedValue(new Error('boom'))

    dialog.open(project)
    const result = await dialog.confirm(removeProject)

    expect(result).toBe(false)
    expect(removeProject).toHaveBeenCalledWith('project-1')
    expect(dialog.isOpen.value).toBe(true)
    expect(dialog.targetProject.value).toEqual(project)
    expect(dialog.deletingProjectId.value).toBe(null)
    expect(dialog.errorMessage.value).toBe('删除失败，请稍后重试。')
  })
})
