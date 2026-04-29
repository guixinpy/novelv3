import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { createProjectFromHome, deleteProject, trackBrowserErrors } from './helpers'

function seedAthenaWorldModel(projectId: string) {
  const rootDir = path.resolve(process.cwd(), '..')
  const backendPython = path.join(rootDir, 'backend', '.venv', 'bin', 'python')
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

    const importResponse = await page.request.post(`/api/v1/projects/${projectId}/athena/ontology/import-setup`)
    expect(importResponse.status()).toBe(200)

    const analyzeResponse = await page.request.post(`/api/v1/projects/${projectId}/athena/evolution/chapters/1/analyze`)
    expect(analyzeResponse.status()).toBe(200)
    expect((await analyzeResponse.json()).created.proposal_items).toBeGreaterThanOrEqual(4)

    const bundlesResponse = await page.request.get(`/api/v1/projects/${projectId}/world-model/proposal-bundles`)
    expect(bundlesResponse.status()).toBe(200)
    const bundlesPayload = await bundlesResponse.json()
    const bundle = bundlesPayload.items[0]
    expect(bundle?.id).toBeTruthy()

    const detailResponse = await page.request.get(`/api/v1/projects/${projectId}/world-model/proposal-bundles/${bundle.id}`)
    expect(detailResponse.status()).toBe(200)
    const detail = await detailResponse.json()
    const lighthouseMention = detail.items.find((item: any) =>
      item.subject_ref === 'loc.旧灯塔' && item.predicate === 'mentioned_in_chapter',
    )
    expect(lighthouseMention?.id).toBeTruthy()

    const reviewResponse = await page.request.post(
      `/api/v1/projects/${projectId}/world-model/proposal-items/${lighthouseMention.id}/review`,
      {
        data: {
          reviewer_ref: 'e2e',
          action: 'approve',
          reason: 'E2E 确认旧灯塔章节提及',
          evidence_refs: ['e2e'],
          edited_fields: {},
        },
      },
    )
    expect(reviewResponse.status()).toBe(200)

    await page.goto(`/projects/${projectId}/athena/projection`)
    await expect(page.getByTestId('workspace-athena')).toBeVisible()
    await expect(page.getByText('loc.旧灯塔')).toBeVisible()
    await expect(page.getByText('mentioned_in_chapter')).toBeVisible()

    await page.goto(`/projects/${projectId}/athena/proposals`)
    await expect(page.getByTestId('world-proposal-bundle-list')).toBeVisible()
    await expect(
      page.getByTestId('world-proposal-item-card').filter({ hasText: 'mentioned_in_chapter' }).first(),
    ).toBeVisible()

    await page.goto(`/projects/${projectId}/hermes`)
    await expect(page.getByTestId('workspace-hermes')).toBeVisible()
    await page.goto(`/projects/${projectId}/athena/projection`)
    await expect(page.getByText('loc.旧灯塔')).toBeVisible()

    browserErrors.expectClean()
  } finally {
    if (projectId) await deleteProject(page, projectId)
  }
})
