import { expect, type Page } from '@playwright/test'

export interface BrowserErrorTracker {
  consoleErrors: string[]
  pageErrors: string[]
  failedApiResponses: string[]
  expectClean: () => void
}

export function trackBrowserErrors(page: Page): BrowserErrorTracker {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  const failedApiResponses: string[] = []

  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'assert') {
      consoleErrors.push(message.text())
    }
  })
  page.on('pageerror', (error) => {
    pageErrors.push(error.message)
  })
  page.on('response', (response) => {
    const url = response.url()
    if (url.includes('/api/') && response.status() >= 400) {
      failedApiResponses.push(`${response.status()} ${url}`)
    }
  })

  return {
    consoleErrors,
    pageErrors,
    failedApiResponses,
    expectClean() {
      expect(consoleErrors, 'console errors').toEqual([])
      expect(pageErrors, 'page errors').toEqual([])
      expect(failedApiResponses, 'failed api responses').toEqual([])
    },
  }
}

export async function createProjectFromHome(page: Page, name: string): Promise<string> {
  await page.goto('/')
  await page.getByTestId('project-create-button').first().click()
  await expect(page.getByTestId('project-create-modal')).toBeVisible()
  await page.getByTestId('project-name-input').getByRole('textbox').fill(name)
  await page.getByTestId('project-create-submit').click()
  await expect(page.getByText(name)).toBeVisible()
  await page.getByText(name).click()
  await expect(page.getByTestId('workspace-hermes')).toBeVisible()

  const match = page.url().match(/\/projects\/([^/]+)\/hermes/)
  if (!match?.[1]) throw new Error(`Unable to extract project id from ${page.url()}`)
  return match[1]
}

export async function deleteProject(page: Page, projectId: string): Promise<void> {
  await page.request.delete(`/api/v1/projects/${projectId}`).catch(() => undefined)
}

export async function installFetchRecorder(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const win = window as typeof window & {
      __workspaceE2EOriginalFetch?: typeof window.fetch
      __workspaceE2ERecords: Array<{ phase: string; method: string; url: string; status: number; durationMs: number }>
      __workspaceE2EPhase: string
      __workspaceE2EInFlight: number
    }
    if (!win.__workspaceE2EOriginalFetch) win.__workspaceE2EOriginalFetch = window.fetch.bind(window)
    win.__workspaceE2ERecords = []
    win.__workspaceE2EPhase = 'idle'
    win.__workspaceE2EInFlight = 0
    window.fetch = async (...args) => {
      const request = args[0]
      const url = typeof request === 'string' ? request : request instanceof Request ? request.url : ''
      const method = args[1]?.method || (request instanceof Request ? request.method : 'GET')
      const start = performance.now()
      win.__workspaceE2EInFlight += 1
      try {
        const response = await win.__workspaceE2EOriginalFetch!(...args)
        if (String(url).includes('/api/')) {
          const parsed = new URL(String(url), location.origin)
          win.__workspaceE2ERecords.push({
            phase: win.__workspaceE2EPhase || 'unknown',
            method,
            url: parsed.pathname + parsed.search,
            status: response.status,
            durationMs: Math.round(performance.now() - start),
          })
        }
        return response
      } finally {
        win.__workspaceE2EInFlight -= 1
      }
    }
  })
}

export async function setFetchPhase(page: Page, phase: string): Promise<void> {
  await page.evaluate((nextPhase) => {
    const win = window as typeof window & { __workspaceE2EPhase: string }
    win.__workspaceE2EPhase = nextPhase
  }, phase)
}

export async function waitForFetchQuiet(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const win = window as typeof window & { __workspaceE2EInFlight?: number }
    return (win.__workspaceE2EInFlight || 0) === 0
  })
  await page.waitForTimeout(350)
}

export async function workspaceRequestSummary(page: Page) {
  return page.evaluate(() => {
    const win = window as typeof window & {
      __workspaceE2ERecords?: Array<{ phase: string; method: string; url: string; status: number; durationMs: number }>
    }
    const summary: Record<string, { requestCount: number; urls: string[]; duplicateUrls: string[] }> = {}
    for (const record of win.__workspaceE2ERecords || []) {
      const item = summary[record.phase] || { requestCount: 0, urls: [], duplicateUrls: [] }
      item.requestCount += 1
      item.urls.push(record.url)
      summary[record.phase] = item
    }
    for (const item of Object.values(summary)) {
      const counts = new Map<string, number>()
      for (const url of item.urls) counts.set(url, (counts.get(url) || 0) + 1)
      item.duplicateUrls = [...counts.entries()]
        .filter(([, count]) => count > 1)
        .map(([url]) => url)
    }
    return summary
  })
}

