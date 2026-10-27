const { test, expect } = require('@playwright/test')
const AxeBuilder = require('@axe-core/playwright').default

// Invented data, not a captured provider response or a real sporting result.
const fixture = {
  id: 9001, utcDate: '2026-10-01T18:00:00Z', status: 'FINISHED',
  competition: { id: 77, name: 'Example League', emblem: 'https://unverified.invalid/league.svg' },
  homeTeam: { id: 101, name: 'Example North', crest: 'https://unverified.invalid/north.svg' },
  awayTeam: { id: 202, name: 'Example South', crest: 'https://unverified.invalid/south.svg' },
  score: { fullTime: { home: 2, away: 1 } },
}
const analysis = {
  home_form: 'G', away_form: 'M', mac_ozeti: 'Synthetic match summary.',
  kg_analizi: 'Synthetic scoring summary.', gol_analizi: 'Synthetic goals summary.',
  ms_egilimi: 'Synthetic result summary.', risk_notu: 'Synthetic limitations.', hizli_bakis: {},
}

async function offline(page, mode = 'matches') {
  const external = []
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route(url => url.origin !== 'http://127.0.0.1:3000', route => {
    external.push(route.request().url())
    return route.abort()
  })
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/matches') {
      if (mode === 'error') return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } })
      return route.fulfill({ json: { matches: mode === 'empty' ? [] : [fixture] } })
    }
    if (path === '/api/matches/form') return route.fulfill({ json: { 9001: { home_form: 'G', away_form: 'M' } } })
    if (path === '/api/match/9001') return route.fulfill({ json: fixture })
    if (path === '/api/match/9001/analysis') return route.fulfill({ json: analysis })
    throw new Error('Unexpected API request: ' + path)
  })
  return { external, errors }
}

test('preserves match browsing and analysis without external assets or data', async ({ page }) => {
  const record = await offline(page)
  await page.goto('/')
  await expect(page.getByTestId('match-card-9001')).toContainText('Example North')
  await expect(page.getByTestId('match-card-9001')).toContainText('Example South')
  await expect(page.getByTestId('match-card-9001').getByRole('img', { name: 'Galibiyet' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Football data provided by the Football-Data.org API' })).toBeVisible()
  await page.getByTestId('match-card-9001').focus()
  await page.getByTestId('match-card-9001').press('Enter')
  await expect(page.getByTestId('match-scoreboard')).toContainText('Example North')
  await expect(page.getByTestId('analysis-title')).toBeVisible()
  await expect(page.getByText('Synthetic match summary.')).toBeVisible()
  await expect(page.locator('img')).toHaveCount(0)
  expect(record.external).toEqual([])
  expect(record.errors).toEqual([])
  const accessibility = await new AxeBuilder({ page }).withRules(['image-alt', 'html-has-lang', 'document-title', 'link-name', 'button-name']).analyze()
  expect(accessibility.violations).toEqual([])
})

test('distinguishes an empty schedule from a provider error and supports retry', async ({ page }) => {
  await offline(page, 'empty')
  await page.goto('/')
  await expect(page.getByTestId('empty-state')).toBeVisible()
  await expect(page.getByTestId('error-state')).toHaveCount(0)
  await page.unroute('**/api/**')
  await offline(page, 'error')
  await page.reload()
  await expect(page.getByTestId('error-state')).toContainText('Synthetic service unavailable')
  await expect(page.getByTestId('empty-state')).toHaveCount(0)
  await page.unroute('**/api/**')
  await offline(page)
  await page.getByTestId('retry-button').click()
  await expect(page.getByTestId('match-card-9001')).toBeVisible()
})

test('shows readable team names and attribution on a narrow screen', async ({ page }) => {
  const record = await offline(page)
  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/match/9001')
  await expect(page.getByTestId('home-team-name')).toHaveText('Example North')
  await expect(page.getByTestId('away-team-name')).toHaveText('Example South')
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375)
  expect(record.external).toEqual([])
  expect(record.errors).toEqual([])
})
