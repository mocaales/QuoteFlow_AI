import { expect, test, type Page } from '@playwright/test';
import { mockApi, signIn } from './fixtures';

// Apple-style upgrade (docs spec section 9): toast details, ActionMenu, tab strip, fonts, reduced motion.
const phone = (page: Page) => page.viewportSize()!.width < 800;
async function open(page: Page, name: string) {
 await page.goto('/'); await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
 if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
 await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name, exact: true }).click();
 await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
 await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}
// Measure after the entry animation; a running scale() shrinks the box.
const settle = (l: import('@playwright/test').Locator) => l.evaluate(el => Promise.all(el.getAnimations({ subtree: true }).map(a => a.finished)));
async function saveItem(page: Page, n = 1) {
 await page.getByRole('button', { name: 'Nova postavka' }).click();
 const d = page.getByRole('dialog');
 await d.getByLabel('Naziv').fill(`Barvanje ${n}`); await d.getByLabel('Opis').fill('Dve plasti'); await d.getByLabel('Vrsta dela').selectOption('v1'); await d.getByLabel('Cena na enoto (€)').fill('18.50');
 await d.getByRole('button', { name: 'Shrani postavko' }).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
}

test.describe('Toast: podrobnosti', () => {
 test.beforeEach(async ({ page }) => { await page.clock.install(); await mockApi(page); await signIn(page); });
 test('en toast z gumbom Zapri obvestilo, v živi regiji, v vidnem polju, brez prekrivanja gumba Meni', async ({ page }) => {
  await open(page, 'Cenik'); await saveItem(page); await page.mouse.move(0, 0);
  const region = page.locator('.toast-region'); await expect(region).toHaveAttribute('role', 'status'); await expect(region).toHaveAttribute('aria-live', 'polite');
  const toast = region.locator('.toast'); await expect(toast).toHaveCount(1); await expect(toast).toContainText('Postavka je shranjena.');
  await expect(toast.getByRole('button', { name: 'Zapri obvestilo' })).toBeVisible(); await expect(page.locator('.notice')).toHaveCount(0);
  const b = (await toast.boundingBox())!, v = page.viewportSize()!;
  expect(b.x).toBeGreaterThanOrEqual(0); expect(b.y).toBeGreaterThanOrEqual(0); expect(b.x + b.width).toBeLessThanOrEqual(v.width);
  if (phone(page)) { const m = (await page.getByRole('button', { name: 'Meni' }).boundingBox())!; expect(b.y >= m.y + m.height || b.x >= m.x + m.width || b.y + b.height <= m.y || b.x + b.width <= m.x, 'toast covers Meni').toBe(true); }
  expect(await toast.evaluate(el => { const r = el.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!hit && el.contains(hit); }), 'toast is hit-testable').toBe(true);
  if (phone(page)) { await settle(toast); const c = (await toast.getByRole('button', { name: 'Zapri obvestilo' }).boundingBox())!; expect(Math.min(c.width, c.height)).toBeGreaterThanOrEqual(44); }
 });
 test('izgine po 5 s, med lebdenjem ostane tudi po 5,5 s', async ({ page }) => {
  await open(page, 'Cenik'); await saveItem(page); const toast = page.locator('.toast-region .toast');
  await expect(toast).toHaveCount(1); await page.clock.runFor(4900); await expect(toast).toHaveCount(1); await page.clock.runFor(300); await expect(toast).toHaveCount(0);
  await saveItem(page, 2); await toast.hover(); await page.clock.runFor(5500); await expect(toast).toHaveCount(1);
 });
 test('štiri hitra shranjevanja pustijo tri obvestila', async ({ page }) => {
  await open(page, 'Cenik'); for (const n of [1, 2, 3, 4]) await saveItem(page, n);
  await expect(page.locator('.toast-region .toast')).toHaveCount(3);
 });
 test('zmanjšano gibanje: toast nima animacije', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }); await open(page, 'Cenik'); await saveItem(page);
  expect(await page.locator('.toast-region .toast').evaluate(el => getComputedStyle(el).animationName)).toBe('none');
 });
 test('neuspeh ostane vrstično opozorilo in ni toast', async ({ page }) => {
  await open(page, 'Cenik');
  await page.route('**/api/podjetja/*/cenik', r => r.request().method() === 'POST' ? r.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Podatkovna baza trenutno ni na voljo."}' }) : r.fallback());
  await page.getByRole('button', { name: 'Nova postavka' }).click(); const d = page.getByRole('dialog');
  await d.getByLabel('Naziv').fill('X'); await d.getByLabel('Opis').fill('Y'); await d.getByLabel('Vrsta dela').selectOption('v1'); await d.getByLabel('Cena na enoto (€)').fill('1');
  await d.getByRole('button', { name: 'Shrani postavko' }).click();
  await expect(page.getByRole('alert').first()).toContainText('ni na voljo'); await expect(page.locator('.toast-region .toast')).toHaveCount(0);
 });
});

test.describe('ActionMenu "Več dejanj" na Projektih', () => {
 test.beforeEach(async ({ page }) => { await mockApi(page); await signIn(page); await open(page, 'Projekti'); });
 const triggers = (page: Page) => page.locator('main button[aria-label^="Več dejanj"]');
 test('vsaka vrstica faze ima natanko en sprožilec, brez gumba z "…"', async ({ page }) => {
  const rows = page.locator('main tbody tr'); const n = await rows.count(); expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) { await expect(rows.nth(i).locator('button[aria-label^="Več dejanj"]')).toHaveCount(1); }
  if (!phone(page)) for (const b of await page.locator('main tbody button').all()) expect(((await b.textContent()) ?? '').trim()).not.toMatch(/^(\.\.\.|…)$/);
 });
 test('sprožilec ima aria-haspopup=menu in aria-expanded; odpre menu z menuitem', async ({ page }) => {
  const t = triggers(page).first(); await expect(t).toHaveAttribute('aria-haspopup', 'menu'); await expect(t).toHaveAttribute('aria-expanded', 'false');
  await t.click(); await expect(t).toHaveAttribute('aria-expanded', 'true');
  const menu = page.getByRole('menu'); await expect(menu).toBeVisible(); await settle(menu); expect(await menu.getByRole('menuitem').count()).toBeGreaterThanOrEqual(2);
  const b = (await menu.boundingBox())!, v = page.viewportSize()!;
  expect(b.x).toBeGreaterThanOrEqual(8 - 1); expect(b.y).toBeGreaterThanOrEqual(8 - 1); expect(b.x + b.width).toBeLessThanOrEqual(v.width - 8 + 1); expect(b.y + b.height).toBeLessThanOrEqual(v.height - 8 + 1);
  if (phone(page)) for (const i of await menu.getByRole('menuitem').all()) expect((await i.boundingBox())!.height).toBeGreaterThanOrEqual(44);
 });
 test('tipkovnica: puščice, Home, End, Escape vrne fokus na sprožilec', async ({ page }) => {
  const t = triggers(page).first(); await t.focus(); await page.keyboard.press('Enter');
  const items = page.getByRole('menuitem'); const n = await items.count(); await expect(items.first()).toBeFocused();
  await page.keyboard.press('ArrowDown'); await expect(items.nth(1)).toBeFocused(); await page.keyboard.press('ArrowUp'); await expect(items.first()).toBeFocused();
  await page.keyboard.press('End'); await expect(items.nth(n - 1)).toBeFocused(); await page.keyboard.press('Home'); await expect(items.first()).toBeFocused();
  await page.keyboard.press('Escape'); await expect(page.getByRole('menu')).toHaveCount(0); await expect(t).toBeFocused(); await expect(t).toHaveAttribute('aria-expanded', 'false');
 });
 test('klik zunaj zapre menu; zadnja vrstica se obrne in ostane v oknu', async ({ page }) => {
  await triggers(page).first().click(); await expect(page.getByRole('menu')).toBeVisible(); await page.mouse.click(2, 2); await expect(page.getByRole('menu')).toHaveCount(0);
  const last = triggers(page).last(); await last.scrollIntoViewIfNeeded(); await last.click();
  const b = (await page.getByRole('menu').boundingBox())!; expect(b.y + b.height).toBeLessThanOrEqual(page.viewportSize()!.height - 8 + 1); expect(b.y).toBeGreaterThanOrEqual(7);
 });
 test('izbira postavke odpre pogled, po zaprtju se fokus vrne na sprožilec', async ({ page }) => {
  const t = triggers(page).first(); await t.click(); await page.getByRole('menuitem', { name: /Uredi/ }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible(); await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0); await expect(t).toBeFocused();
 });
});

test.describe('Zavihki, pisava, gibanje', () => {
 test('štirje zavihki admina na 390: izbrani je v celoti viden, trak ima data-more', async ({ page }) => {
  await mockApi(page); await signIn(page); await open(page, 'Podjetja in pravice');
  const tabs = page.getByRole('tablist').getByRole('tab'); await expect(tabs).toHaveCount(4);
  if (phone(page)) await expect(page.getByRole('tablist')).toHaveAttribute('data-more', /.*/);
  await tabs.last().click(); await expect(tabs.last()).toHaveAttribute('aria-selected', 'true');
  const b = (await tabs.last().boundingBox())!, v = page.viewportSize()!; expect(b.x).toBeGreaterThanOrEqual(0); expect(b.x + b.width).toBeLessThanOrEqual(v.width);
 });
 test('pisava je sistemska in ni zahtev na fonts.googleapis.com', async ({ page }) => {
  const external: string[] = []; page.on('request', r => { if (/fonts\.(googleapis|gstatic)\.com/.test(r.url())) external.push(r.url()); });
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await mockApi(page); await signIn(page); await page.goto('/'); await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => getComputedStyle(document.body).fontFamily)).toMatch(/^"?-apple-system/); expect(external).toEqual([]);
 });
 test('zmanjšano gibanje: po odprtju predala ni animacij', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }); await mockApi(page); await signIn(page); await open(page, 'Cenik');
  await page.getByRole('button', { name: 'Nova postavka' }).click(); await expect(page.getByRole('dialog')).toBeVisible();
  expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
 });
});
