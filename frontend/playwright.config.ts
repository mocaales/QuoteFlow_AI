import { defineConfig, devices } from '@playwright/test';
// Browser checks of the visual system. The API and Supabase Auth are mocked in e2e/fixtures.ts,
// so the suite needs no backend or credentials; screenshots land in test-results/screens/.
export default defineConfig({
 testDir: './e2e',
 outputDir: './test-results/playwright',
 fullyParallel: true,
 reporter: [['list']],
 use: { baseURL: 'http://127.0.0.1:5174', locale: 'sl-SI', timezoneId: 'Europe/Ljubljana' },
 projects: [
  { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  { name: 'phone', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, hasTouch: true } },
 ],
 webServer: { command: 'npx vite --host 127.0.0.1 --port 5174 --strictPort', url: 'http://127.0.0.1:5174', reuseExistingServer: true },
});
