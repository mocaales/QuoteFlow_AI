import { expect, test, type Page } from '@playwright/test';
import { mockApi, signIn } from './fixtures';

// The visual system as measurable rules (docs/razvoj/frontend-arhitektura.md, "Vizualni sistem").
// Every screen is checked at desktop and phone width and saved for review in test-results/screens/.
type Screen = 'pregled' | 'cenik' | 'zaloge' | 'materiali' | 'admin' | 'prosnja';
const nav: Record<Exclude<Screen, 'pregled'>, string> = { cenik: 'Cenik', zaloge: 'Zaloge', materiali: 'Materiali', admin: 'Podjetja in pravice', prosnja: 'Prošnja za mojstra' };
const phone = (page: Page) => page.viewportSize()!.width < 800;

async function open(page: Page, screen: Screen) {
 await page.goto('/');
 await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
 if (screen === 'pregled') return;
 if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
 await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: nav[screen] }).click();
 await expect(page.getByRole('heading', { level: 1, name: nav[screen] })).toBeVisible();
 await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

async function audit(page: Page) {
 return page.evaluate(({ isPhone }) => {
  const problems: string[] = [];
  const rgba = (value: string) => { const n = value.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0, 0]; return [n[0], n[1], n[2], n[3] ?? 1]; };
  const background = (el: Element | null): number[] => {
   for (; el; el = el.parentElement) { const c = rgba(getComputedStyle(el).backgroundColor); if (c[3] > 0.5) return c; }
   return [255, 255, 255, 1];
  };
  const luminance = ([r, g, b]: number[]) => { const f = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const blend = (fg: number[], bg: number[]) => fg.slice(0, 3).map((v, i) => v * fg[3] + bg[i] * (1 - fg[3]));
  const contrast = (a: number[], b: number[]) => { const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
  const visible = (el: Element) => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1 && el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && !el.closest('[aria-hidden="true"], .sr-only'); };
  const name = (el: Element) => `<${el.tagName.toLowerCase()}> "${(el.textContent ?? '').trim().slice(0, 40)}"`;

  const h1 = [...document.querySelectorAll('h1')].filter(visible);
  if (h1.length !== 1) problems.push(`expected one visible h1, found ${h1.length}`);
  for (const h of h1) { const size = parseFloat(getComputedStyle(h).fontSize); if (size < 18 || size > 32) problems.push(`h1 at ${size}px (app titles are 18-32px)`); }
  if (document.documentElement.scrollWidth > innerWidth + 1) problems.push(`page scrolls sideways: ${document.documentElement.scrollWidth}px > ${innerWidth}px`);

  for (const el of document.querySelectorAll('body *')) {
   const own = [...el.childNodes].filter(n => n.nodeType === Node.TEXT_NODE).map(n => n.textContent ?? '').join('').trim();
   if (!own || !visible(el)) continue;
   const style = getComputedStyle(el);
   const size = parseFloat(style.fontSize);
   if (size < 12) problems.push(`text under 12px (${size}px): ${name(el)}`);
   if (parseFloat(style.letterSpacing) > 0.5) problems.push(`tracked letters (${style.letterSpacing}): ${name(el)}`);
   if (style.textTransform === 'uppercase' || /^[A-ZČŠŽĆĐ ]{6,}$/.test(own)) problems.push(`uppercase label: ${name(el)}`);
   if (!el.closest(':disabled')) {
    const bg = background(el), ratio = contrast(blend(rgba(style.color), bg), bg);
    if (ratio < 4.5) problems.push(`contrast ${ratio.toFixed(2)}:1 under 4.5:1: ${name(el)}`);
   }
  }

  for (const table of document.querySelectorAll('table')) {
   if (!visible(table)) continue;
   const numeric = new Set<number>();
   for (const row of table.querySelectorAll('tbody tr')) [...row.children].forEach((cell, index) => {
    const text = (cell.textContent ?? '').trim();
    if (index === 0 || !(/€|%/.test(text) || /^-?\d/.test(text))) return;
    numeric.add(index);
    const style = getComputedStyle(cell);
    if (!['right', 'end'].includes(style.textAlign)) problems.push(`numeric cell not right-aligned: ${name(cell)}`);
    if (!style.fontVariantNumeric.includes('tabular-nums')) problems.push(`numeric cell without tabular figures: ${name(cell)}`);
   });
   const head = table.querySelectorAll('thead th');
   for (const index of numeric) if (head[index] && !['right', 'end'].includes(getComputedStyle(head[index]).textAlign)) problems.push(`numeric header not right-aligned: ${name(head[index])}`);
  }

  const navigation = document.querySelector('nav[aria-label="Glavna navigacija"]');
  if (navigation && visible(navigation) && luminance(background(navigation)) < 0.8) problems.push('navigation sits on a dark ground');
  for (const el of document.querySelectorAll('button, a, select, input:not([type=checkbox])')) {
   if (!visible(el)) continue;
   const height = el.getBoundingClientRect().height, min = isPhone ? 40 : 28;
   if (height < min - 0.5) problems.push(`control ${height.toFixed(0)}px tall (min ${min}px): ${name(el)}`);
  }
  // Icon-only buttons need a name for assistive tech and a visible tooltip for everyone else.
  for (const el of document.querySelectorAll('button')) {
   if (!visible(el) || (el.textContent ?? '').trim()) continue;
   if (!el.getAttribute('aria-label')) problems.push(`icon button without accessible name: ${el.outerHTML.slice(0, 60)}`);
   if (!el.getAttribute('data-tip')) problems.push(`icon button without tooltip: ${el.getAttribute('aria-label')}`);
  }
  return [...new Set(problems)];
 }, { isPhone: phone(page) });
}

async function check(page: Page, screen: string, project: string) {
 await page.evaluate(async () => { await document.fonts.ready; await Promise.allSettled(document.getAnimations().map(a => a.finished)); });
 await page.screenshot({ path: `test-results/screens/${screen}-${project}.png`, fullPage: true });
 expect(await audit(page)).toEqual([]);
}

test.describe('Prijavljen mojster in admin', () => {
 test.beforeEach(async ({ page }) => { await mockApi(page); await signIn(page); });
 for (const screen of ['pregled', 'cenik', 'zaloge', 'materiali', 'admin', 'prosnja'] as const) {
  test(`zaslon ${screen} ustreza vizualnemu sistemu`, async ({ page }, info) => {
   await open(page, screen);
   await check(page, screen, info.project.name);
  });
 }

 test('prošnja za mojstra pokaže zgodovino in obrazec', async ({ page }, info) => {
  await open(page, 'prosnja');
  await expect(page.getByText('Parketarstvo Ana s.p.')).toBeVisible();
  await expect(page.getByText('Zavrnjena')).toBeVisible();
  for (const label of ['Naziv podjetja', 'Matična številka', 'Naslov podjetja', 'Davčna številka (neobvezno)']) await expect(page.getByLabel(label)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Oddaj prošnjo' })).toBeVisible();
  await check(page, 'prosnja-obrazec', info.project.name);
 });

 test('admin vidi prošnje mojstrov z gumbi Odobri in Zavrni samo pri oddani', async ({ page }, info) => {
  await open(page, 'admin');
  await expect(page.getByRole('heading', { name: 'Prošnje mojstrov' })).toBeVisible();
  await expect(page.getByText('marko@example.test').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Odobri Elektro Kos d.o.o.' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zavrni Elektro Kos d.o.o.' })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Odobri Zidarstvo/ })).toHaveCount(0);
  await check(page, 'admin-prosnje', info.project.name);
 });

 test('ikona za urejanje ob prehodu pokaže namig', async ({ page }) => {
  test.skip(phone(page), 'Telefon nima prehoda z miško; ime gumba ostane dostopno.');
  await open(page, 'cenik');
  const edit = page.getByRole('button', { name: 'Uredi Rušenje estriha' });
  await expect(edit).toHaveAttribute('data-tip', 'Uredi');
  await edit.hover();
  await expect.poll(() => edit.evaluate(el => getComputedStyle(el, '::after').content)).toBe('"Uredi"');
  const tip = await edit.evaluate(el => { const s = getComputedStyle(el, '::after'); return { color: s.color, background: s.backgroundColor, size: parseFloat(s.fontSize) }; });
  expect(tip.size).toBeGreaterThanOrEqual(12);
  expect(tip.background).not.toBe(tip.color);
 });

 test('urejanje postavke odpre stranski panel', async ({ page }, info) => {
  await open(page, 'cenik');
  await page.getByRole('button', { name: 'Nova postavka' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await check(page, 'cenik-panel', info.project.name);
 });

 test('material in zaloga imata pregleden panel, tudi po osvežitvi pravic', async ({ page }, info) => {
  await open(page, 'materiali');
  await page.getByRole('button', { name: 'Nov material' }).click();
  await page.getByLabel('Naziv', { exact: true }).fill('Neshranjeno lepilo');
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByLabel('Naziv', { exact: true })).toHaveValue('Neshranjeno lepilo');
  await check(page, 'material-panel', info.project.name);
  await page.keyboard.press('Escape');
  if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
  await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: 'Zaloge' }).click();
  await page.getByRole('button', { name: 'Zaloga za Lepilo za ploščice: Celje' }).click();
  await expect(page.getByLabel('Količina (kg)')).toHaveValue('0');
  await expect(page.getByLabel('Lokacija')).toHaveValue('Celje');
  await check(page, 'zaloga-panel', info.project.name);
 });

 test('navigacija se na telefonu zloži v meni', async ({ page }) => {
  await page.goto('/');
  const menu = page.getByRole('button', { name: 'Meni' }), navigation = page.getByRole('navigation', { name: 'Glavna navigacija' });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  if (!phone(page)) { await expect(menu).toBeHidden(); await expect(navigation).toBeVisible(); return; }
  await expect(navigation).toBeHidden();
  const title = await page.getByRole('heading', { level: 1 }).boundingBox();
  expect(title!.y).toBeLessThan(844 * 0.3);
  await menu.click();
  await expect(navigation).toBeVisible();
  await navigation.getByRole('button', { name: 'Cenik' }).click();
  await expect(navigation).toBeHidden();
  await expect(page.getByRole('heading', { level: 1, name: 'Cenik' })).toBeVisible();
 });
});

test('napaka pri nalaganju cenika ohrani okvir zaslona', async ({ page }, info) => {
 await mockApi(page, { catalogStatus: 503 }); await signIn(page);
 await open(page, 'cenik').catch(() => undefined);
 await expect(page.getByRole('alert')).toContainText('Podatkovna baza trenutno ni na voljo.');
 await expect(page.getByRole('heading', { name: 'Dodajte prvo postavko' })).toHaveCount(0);
 await check(page, 'cenik-napaka', info.project.name);
});

test('prijava ustreza vizualnemu sistemu', async ({ page }, info) => {
 await mockApi(page);
 await page.goto('/');
 await expect(page.getByRole('heading', { level: 1, name: 'Prijava' })).toBeVisible();
 await check(page, 'prijava', info.project.name);
});
