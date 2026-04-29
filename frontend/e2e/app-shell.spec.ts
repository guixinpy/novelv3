import { expect, test } from '@playwright/test'

test('serves the app shell from FastAPI static build', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '项目' })).toBeVisible()
})
