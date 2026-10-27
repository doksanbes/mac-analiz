const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './tests',
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:3000', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run start',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: false,
    timeout: 120000,
    env: { NEXT_TELEMETRY_DISABLED: '1', NEXT_PUBLIC_BACKEND_URL: '' },
  },
})
