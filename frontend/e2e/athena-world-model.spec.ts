import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { createProjectFromHome, deleteProject, trackBrowserErrors } from './helpers'

function seedAthenaWorldModel(projectId: string) {
  const rootDir = path.resolve(process.cwd(), '..')
  const backendPython =
    process.platform === 'win32'
      ? path.join(rootDir, 'backend', '.venv', 'Scripts', 'python.exe')
      : path.join(rootDir, 'backend', '.venv', 'bin', 'python')
  execFileSync(
    process.env.PYTHON || backendPython,
    [path.join(rootDir, 'scripts', 'seed_athena_e2e.py'), projectId],
    {
      cwd: rootDir,
      env: {
        ...process.env,
        PYTHONPATH: path.join(rootDir, 'backend'),
      },
      stdio: 'pipe',
    },
  )
}

test('renders Athena projection and proposal workbench from local world-model data', async ({ page }) => {
  const browserErrors = trackBrowserErrors(page)
  let projectId = ''

  try {
    projectId = await createProjectFromHome(page, `E2E Athena ${Date.now()}`)
    seedAthenaWorldModel(projectId)

    await page.goto(`/projects/${projectId}/athena`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await expect(page.getByTestId('athena-overview-import-preview')).toBeVisible()

    const importResponse = await page.request.post(`/api/v1/projects/${projectId}/athena/ontology/import-setup`)
    expect(importResponse.status()).toBe(200)

    const analyzeResponse = await page.request.post(`/api/v1/projects/${projectId}/athena/evolution/chapters/1/analyze`)
    expect(analyzeResponse.status()).toBe(200)
    expect((await analyzeResponse.json()).created.proposal_items).toBeGreaterThanOrEqual(4)

    const reindexResponse = await page.request.post(`/api/v1/projects/${projectId}/athena/retrieval/reindex`)
    expect(reindexResponse.status()).toBe(200)

    const bundlesResponse = await page.request.get(`/api/v1/projects/${projectId}/world-model/proposal-bundles`)
    expect(bundlesResponse.status()).toBe(200)
    const bundlesPayload = await bundlesResponse.json()
    const bundle = bundlesPayload.items[0]
    expect(bundle?.id).toBeTruthy()

    const detailResponse = await page.request.get(`/api/v1/projects/${projectId}/world-model/proposal-bundles/${bundle.id}`)
    expect(detailResponse.status()).toBe(200)
    const detail = await detailResponse.json()
    const pendingBeforeReview = detail.items.filter((item: any) =>
      ['pending', 'needs_edit'].includes(item.item_status),
    ).length
    const lighthouseMention = detail.items.find((item: any) =>
      item.subject_ref === 'loc.旧灯塔' && item.predicate === 'mentioned_in_chapter',
    )
    expect(lighthouseMention?.id).toBeTruthy()

    await page.goto(`/projects/${projectId}/athena`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await expect(page.getByTestId('athena-overview')).toBeVisible()
    await expect(page.getByTestId('athena-overview-metric-pending_item_count')).toContainText(String(pendingBeforeReview))
    await expect(page.getByTestId('athena-overview-next-action')).toContainText('处理待审世界模型提案')

    await page.getByTestId('athena-overview-next-action').click()
    await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/athena/review\\?view=proposals$`))
    await expect(page.getByTestId('world-proposal-bundle-list')).toBeVisible()

    const lighthouseCard = page
      .getByTestId('world-proposal-item-card')
      .filter({ hasText: 'loc.旧灯塔.mentioned_in_chapter' })
      .first()
    await expect(lighthouseCard).toBeVisible()
    await lighthouseCard.getByRole('button', { name: '通过', exact: true }).click()
    await expect(lighthouseCard).toHaveAttribute('data-item-status', 'approved')

    await page.goto(`/projects/${projectId}/athena`)
    await expect(page.getByTestId('athena-overview')).toBeVisible()
    await expect(page.getByTestId('athena-overview-metric-pending_item_count')).toContainText(String(pendingBeforeReview - 1))

    await page.goto(`/projects/${projectId}/athena/catalog?view=nodes&tool=retrieval`)
    await page.getByPlaceholder('搜索角色、规则、伏笔、章节事实').fill('旧灯塔')
    await page.getByRole('button', { name: '搜索' }).click()
    await expect(page.getByText('章节原文').first()).toBeVisible()
    await expect(page.getByText('可用于核对设定').first()).toBeVisible()

    await page.goto(`/projects/${projectId}/athena/truth?view=projection`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await expect(page.getByText('地点').first()).toBeVisible()
    await expect(page.getByText('loc.旧灯塔')).toBeVisible()
    await expect(page.getByText('mentioned_in_chapter')).toBeVisible()

    await page.goto(`/projects/${projectId}/athena/review?view=proposals`)
    await expect(page.getByTestId('world-proposal-bundle-list')).toBeVisible()
    await expect(
      page.getByTestId('world-proposal-item-card').filter({ hasText: 'mentioned_in_chapter' }).first(),
    ).toBeVisible()

    await page.goto(`/projects/${projectId}/hermes`)
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()
    await page.goto(`/projects/${projectId}/athena/truth?view=projection`)
    await expect(page.getByText('loc.旧灯塔')).toBeVisible()

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})
