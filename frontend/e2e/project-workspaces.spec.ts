import { expect, test } from '@playwright/test'
import {
  createProjectFromHome,
  deleteProject,
  installFetchRecorder,
  setFetchPhase,
  trackBrowserErrors,
  waitForFetchQuiet,
  workspaceRequestSummary,
} from './helpers'

test('creates a project and switches between core workspaces', async ({ page }) => {
  const browserErrors = trackBrowserErrors(page)
  let projectId = ''

  try {
    projectId = await createProjectFromHome(page, `E2E 工作区 ${Date.now()}`)

    await page.getByTestId('workspace-nav-athena').click()
    await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/athena/overview$`))
    await expect(page.getByTestId('workspace-athena')).toBeVisible()

    await page.getByTestId('workspace-nav-manuscript').click()
    await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/manuscript$`))
    await expect(page.getByTestId('workspace-manuscript')).toBeVisible()

    await page.getByTestId('workspace-nav-hermes').click()
    await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/hermes$`))
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})

test('keeps workspace switching within request budget', async ({ page }) => {
  const browserErrors = trackBrowserErrors(page)
  let projectId = ''

  try {
    await installFetchRecorder(page)
    projectId = await createProjectFromHome(page, `E2E 请求预算 ${Date.now()}`)

    await setFetchPhase(page, 'cold_hermes')
    await page.goto(`/projects/${projectId}/hermes`)
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()
    await waitForFetchQuiet(page)

    await setFetchPhase(page, 'hermes_to_athena')
    await page.goto(`/projects/${projectId}/athena`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await waitForFetchQuiet(page)

    await setFetchPhase(page, 'athena_to_hermes')
    await page.goto(`/projects/${projectId}/hermes`)
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()
    await waitForFetchQuiet(page)

    await setFetchPhase(page, 'rapid_switch')
    for (const path of [
      `/projects/${projectId}/athena`,
      `/projects/${projectId}/hermes`,
      `/projects/${projectId}/manuscript`,
      `/projects/${projectId}/hermes`,
      `/projects/${projectId}/athena`,
      `/projects/${projectId}/manuscript`,
      `/projects/${projectId}/hermes`,
    ]) {
      await page.goto(path)
      await page.waitForTimeout(120)
    }
    await waitForFetchQuiet(page)

    const summary = await workspaceRequestSummary(page)
    expect(summary.cold_hermes?.requestCount || 0).toBeLessThanOrEqual(1)
    expect(summary.hermes_to_athena?.requestCount || 0).toBeLessThanOrEqual(2)
    expect(summary.athena_to_hermes?.requestCount || 0).toBeLessThanOrEqual(1)
    expect(summary.rapid_switch?.requestCount || 0).toBeLessThanOrEqual(8)
    for (const item of Object.values(summary)) {
      expect(item.duplicateUrls).toEqual([])
    }

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})

test('refreshes Hermes and Athena without optional-resource 404 noise', async ({ page }) => {
  const browserErrors = trackBrowserErrors(page)
  let projectId = ''

  try {
    projectId = await createProjectFromHome(page, `E2E 刷新恢复 ${Date.now()}`)

    await page.reload()
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()

    await page.goto(`/projects/${projectId}/athena`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await page.reload()
    await expect(page.getByTestId('workspace-athena')).toBeVisible()

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})
