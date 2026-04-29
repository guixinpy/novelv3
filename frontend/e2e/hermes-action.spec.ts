import { expect, test } from '@playwright/test'
import { createProjectFromHome, deleteProject, trackBrowserErrors } from './helpers'

test('confirms a Hermes action through the background task path', async ({ page }) => {
  const browserErrors = trackBrowserErrors(page)
  let projectId = ''

  try {
    projectId = await createProjectFromHome(page, `E2E Action ${Date.now()}`)

    await page.getByTestId('chat-input').fill('/setup 主角是植物学家')
    await page.getByTestId('chat-send').click()

    await expect(page.getByTestId('pending-action-card')).toBeVisible()
    await page.getByTestId('pending-action-confirm').click()

    await expect(page.getByTestId('chat-input')).toBeEnabled({ timeout: 30_000 })
    await expect(page.getByText(/API key not configured|生成设定完成|已取消/)).toBeVisible({ timeout: 30_000 })

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})
