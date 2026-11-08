import { expect, test, type Page } from '@playwright/test';
import { customerQuote, mockApi, quoteFull, signIn, type Mock } from './fixtures';
import { rowAction } from './layout';

// WCAG 2.2 AA audit of US-04..US-07 (project items and izmere, quote preview and send, customer decision, execution, invoices) with explicit assertions (model v3).
// Tests tagged [A11Y-nn] pin a real finding and FAIL until the owner fixes it; unmarked tests document checks that pass.
// Run alone: npx playwright test e2e/a11y-quotes-invoices.spec.ts --output=<scratch dir>.

type Screen = 'projekti' | 'moji' | 'cenik' | 'vrste';
const nav: Record<Screen, string> = { projekti: 'Projekti', moji: 'Moji projekti', cenik: 'Cenik', vrste: 'Vrste dela' };
const phone = (page: Page) => page.viewportSize()!.width < 800;

declare global { interface Window { __a: { rgba: (v: string) => number[]; bg: (el: Element | null) => number[]; ratio: (a: number[], b: number[]) => number; visible: (el: Element) => boolean; label: (el: Element) => string } } }

test.beforeEach(async ({ page }) => {
 await page.addInitScript(() => {
  const rgba = (value: string) => { const n = value.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0, 0]; return [n[0], n[1], n[2], n[3] ?? 1]; };
  const bg = (el: Element | null): number[] => { for (; el; el = el.parentElement) { const c = rgba(getComputedStyle(el).backgroundColor); if (c[3] > 0.5) return c; } return [255, 255, 255, 1]; };
  const lum = ([r, g, b]: number[]) => { const f = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const ratio = (a: number[], b: number[]) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
  const visible = (el: Element) => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1 && el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && !el.closest('[aria-hidden="true"], .sr-only'); };
  const label = (el: Element) => (el.getAttribute('aria-label') ?? (el.textContent ?? '')).trim();
  (window as unknown as Window).__a = { rgba, bg, ratio, visible, label };
 });
});

// Opacity/transform animations (drawer-in, fade-in) distort geometry and visibility checks; measure the settled page.
const settle = (page: Page) => page.evaluate(async () => { await document.fonts.ready; await Promise.allSettled(document.getAnimations().map(a => a.finished)); });

async function open(page: Page, screen: Screen) {
 await page.goto('/');
 await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
 if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
 await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: nav[screen], exact: true }).click();
 await expect(page.getByRole('heading', { level: 1, name: nav[screen] })).toBeVisible();
 await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}
async function masterQuote(page: Page, quote: Mock['quote'] = 'osnutek') {
 await mockApi(page, { quote }); await signIn(page); await open(page, 'projekti');
 await rowAction(page, 'Obnova kopalnice', 'Ponudba');
 await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
}
async function customer(page: Page) {
 await mockApi(page, { customerQuote: 'poslana' }); await signIn(page); await open(page, 'moji');
 await page.getByRole('button', { name: 'Ponudba Menjava oken' }).click();
 await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
}
async function progress(page: Page, state: 'termin' | 'izvedba') {
 await mockApi(page, { progress: state }); await signIn(page); await open(page, 'projekti');
 await rowAction(page, 'Nov estrih', 'Izvedba');
 await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible();
}
async function invoicePanel(page: Page, invoice: NonNullable<Mock['invoice']>) {
 await mockApi(page, { invoice }); await signIn(page); await open(page, 'projekti');
 await rowAction(page, 'Nov estrih', 'Račun');
 await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible();
}
async function customerInvoice(page: Page) {
 await mockApi(page, { customerInvoice: 'izdan' }); await signIn(page); await open(page, 'moji');
 await page.getByRole('button', { name: 'Račun Estrih v kleti' }).click();
 await expect(page.getByRole('heading', { name: /R-2026-001/ })).toBeVisible();
}

async function itemsScreen(page: Page) {
 await mockApi(page, {}); await signIn(page); await open(page, 'projekti');
 await rowAction(page, 'Obnova kopalnice', 'Postavke');
 await expect(page.getByRole('heading', { level: 1, name: 'Obnova kopalnice' })).toBeVisible();
 // The openers stay disabled while the items load; focus() on a disabled button is a silent no-op, so wait until they are usable.
 await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
 for (const name of ['Dodaj iz cenika', 'Nova postavka']) await expect(page.getByRole('button', { name })).toBeEnabled();
}
async function fillItem(page: Page) {
 const d = page.getByRole('dialog');
 for (const [label, value] of [['Naziv', 'Beljenje'], ['Opis', 'Dve plasti'], ['Cena na enoto', '10'], ['Količina', '1'], ['Stopnja DDV (%)', '22']]) await d.getByLabel(label).fill(value);
 await d.getByLabel('Vrsta dela').selectOption({ label: 'Beljenje' }); await d.getByLabel('Enota').selectOption({ label: 'm²' });
 return d;
}
// Drawers of the project items screen: [opener, ...]
const OPENERS = ['Dodaj iz cenika', 'Nova postavka', 'Izmere Polaganje keramike'];

const scenarios: [string, (page: Page) => Promise<void>][] = [
 ['ponudba-osnutek', page => masterQuote(page)],
 ['postavke-seznam', itemsScreen],
 ['postavke-cenik-panel', async page => { await itemsScreen(page); await page.getByRole('button', { name: 'Dodaj iz cenika' }).click(); await expect(page.getByRole('dialog').getByText('Polaganje keramike')).toBeVisible(); }],
 ['postavka-obrazec', async page => { await itemsScreen(page); await page.getByRole('button', { name: 'Nova postavka' }).click(); await expect(page.getByRole('dialog').getByLabel('Naziv')).toBeVisible(); }],
 ['izmere-panel', async page => { await itemsScreen(page); await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click(); await expect(page.getByRole('dialog').getByLabel('Dolžina')).toBeVisible(); }],
 ['vrste-dela', async page => { await mockApi(page, {}); await signIn(page); await open(page, 'vrste'); }],
 ['vrsta-dela-materiali', async page => { await mockApi(page, {}); await signIn(page); await open(page, 'vrste'); await page.getByRole('button', { name: 'Materiali Keramika' }).click(); await expect(page.getByRole('dialog').getByLabel('Material')).toBeVisible(); }],
 ['cenik', async page => { await mockApi(page, {}); await signIn(page); await open(page, 'cenik'); }],
 ['ponudba-stranka', customer],
 ['ponudba-stranka-potrditev', async page => { await customer(page); await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click(); await expect(page.getByRole('button', { name: 'Potrdi sprejem' })).toBeVisible(); }],
 ['potek-termin', page => progress(page, 'termin')],
 ['potek-izvedba', page => progress(page, 'izvedba')],
 ['racun-pripravljen', page => invoicePanel(page, 'osnutek-pripravljen')],
 ['racun-izdan', page => invoicePanel(page, 'izdan')],
 ['racun-stranka', customerInvoice],
 ['projekti-seznam', async page => { await mockApi(page, {}); await signIn(page); await open(page, 'projekti'); }],
 ['moji-projekti', async page => { await mockApi(page, {}); await signIn(page); await open(page, 'moji'); }],
];

// ---------------------------------------------------------------- structure, names, labels, headings (every screen)
for (const [name, setup] of scenarios) {
 test(`struktura in imena: ${name}`, async ({ page }) => {
  await setup(page); await settle(page);
  const result = await page.evaluate(() => {
   const { visible, label } = window.__a, problems: string[] = [];
   if (document.documentElement.lang !== 'sl') problems.push(`html lang is "${document.documentElement.lang}"`);
   const h1 = [...document.querySelectorAll('h1')].filter(visible);
   if (h1.length !== 1) problems.push(`visible h1 count ${h1.length}`);
   let last = 0;
   for (const h of [...document.querySelectorAll('main :is(h1,h2,h3,h4), dialog :is(h2,h3,h4)')].filter(visible)) { const level = +h.tagName[1]; if (last && level > last + 1) problems.push(`heading jumps h${last} -> h${level}: ${h.textContent}`); last = level; }
   for (const el of document.querySelectorAll('main button, main a[href], dialog button')) {
    if (!visible(el)) continue;
    const text = (el.textContent ?? '').trim(), aria = el.getAttribute('aria-label');
    if (!text && !aria) problems.push(`unnamed control ${el.outerHTML.slice(0, 80)}`);
    if (text && aria && !aria.replace(/\s/g, '').toLowerCase().includes(text.replace(/\s/g, '').toLowerCase())) problems.push(`label-in-name (2.5.3): visible "${text}" vs aria-label "${aria}"`);
    if (!text && !(el.getAttribute('data-tip'))) problems.push(`icon button without tooltip: ${aria}`);
   }
   for (const el of document.querySelectorAll('main :is(input:not([type=hidden]), select, textarea), dialog :is(input:not([type=hidden]), select, textarea)')) {
    if (!visible(el)) continue;
    const input = el as HTMLInputElement;
    if (!(input.labels?.length || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))) problems.push(`input without label: ${el.outerHTML.slice(0, 80)}`);
   }
   for (const table of document.querySelectorAll('table')) {
    if (!visible(table)) continue;
    if (!table.querySelector('caption')?.textContent?.trim()) problems.push('table without caption');
    for (const th of table.querySelectorAll('th')) if (!label(th)) problems.push('empty table header');
   }
   for (const badge of document.querySelectorAll('.status-badge')) if (visible(badge) && !(badge.textContent ?? '').trim()) problems.push('status badge without text');
   for (const live of document.querySelectorAll('.alert')) if (live.getAttribute('role') !== 'alert') problems.push('.alert without role=alert');
   for (const live of document.querySelectorAll('.notice')) if (!['status', 'alert'].includes(live.getAttribute('role') ?? '')) problems.push('.notice without role=status');
   const current = document.querySelector('nav[aria-label="Glavna navigacija"] [aria-current="page"]');
   if (!current) problems.push('navigation has no aria-current=page item');
   for (const region of document.querySelectorAll('*')) {
    const s = getComputedStyle(region);
    if (['auto', 'scroll'].includes(s.overflowX) && region.scrollWidth > region.clientWidth + 1 && visible(region) && !region.hasAttribute('tabindex') && !region.querySelector('a[href],button:not(:disabled),input,select,textarea,[tabindex]')) problems.push(`scrollable region not keyboard reachable: ${region.className}`);
   }
   return problems;
  });
  expect(result).toEqual([]);
 });

 test(`[A11Y-14] ciljne velikosti 24px (2.5.8) in 44px na telefonu: ${name}`, async ({ page }) => {
  await setup(page); await settle(page);
  const isPhone = phone(page);
  const small = await page.evaluate(({ isPhone }) => {
   const { visible, label } = window.__a, out: string[] = [];
   // WCAG 2.5.8 needs 24px; the project asks 44px on the phone (docs/razvoj/frontend-arhitektura.md and the audit brief).
   const min = isPhone ? 44 : 24;
   for (const el of document.querySelectorAll('main :is(button, a[href], select, textarea, input:not([type=checkbox]):not([type=hidden])), dialog :is(button, select, textarea, input:not([type=checkbox]):not([type=hidden]))')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.height < min - 0.5 || r.width < min - 0.5) out.push(`${el.tagName.toLowerCase()} "${label(el).slice(0, 30)}" ${r.width.toFixed(0)}x${r.height.toFixed(0)}`);
   }
   return out;
  }, { isPhone });
  expect(small, `controls under ${isPhone ? 44 : 24}px`).toEqual([]);
 });

 test(`[A11Y-04] mejna kontrast polj 3:1 (1.4.11): ${name}`, async ({ page }) => {
  await setup(page); await settle(page);
  const weak = await page.evaluate(() => {
   const { visible, rgba, bg, ratio } = window.__a, out: string[] = [];
   for (const el of document.querySelectorAll('main :is(input:not([type=checkbox]):not([type=hidden]), select, textarea), dialog :is(input:not([type=checkbox]):not([type=hidden]), select, textarea)')) {
    if (!visible(el)) continue;
    const s = getComputedStyle(el), border = rgba(s.borderTopColor), ground = bg(el.parentElement), fill = rgba(s.backgroundColor);
    const r = ratio(border, ground), f = ratio(fill, ground);
    if (parseFloat(s.borderTopWidth) > 0 && r < 3 && f < 3) out.push(`${(el as HTMLInputElement).name || el.tagName}: border ${s.borderTopColor} on ${ground.slice(0, 3)} = ${r.toFixed(2)}:1`);
   }
   return out;
  });
  expect(weak, 'input boundaries below 3:1').toEqual([]);
 });

 test(`vidna fokusna oznaka 2px accent (2.4.7, 2.4.11): ${name}`, async ({ page }) => {
  await setup(page); await settle(page);
  const seen = new Set<string>(), problems: string[] = [];
  const dialog = await page.getByRole('dialog').count();
  if (!dialog) await page.getByRole('main').getByRole('heading').first().evaluate(el => { el.setAttribute('tabindex', '-1'); (el as HTMLElement).focus(); el.removeAttribute('tabindex'); });
  for (let i = 0; i < 40; i++) {
   await page.keyboard.press('Tab');
   const info = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement, { ratio, bg, rgba } = window.__a;
    if (!el || el === document.body) return null;
    const s = getComputedStyle(el), out = rgba(s.outlineColor), ring = ratio(out, bg(el.parentElement));
    return { key: `${el.tagName}|${el.getAttribute('aria-label') ?? el.textContent?.trim().slice(0, 30) ?? ''}|${(el as HTMLInputElement).name ?? ''}`, w: parseFloat(s.outlineWidth), st: s.outlineStyle, color: s.outlineColor, ring, main: !!el.closest('main, dialog') };
   });
   if (!info) continue;
   if (seen.has(info.key)) break; seen.add(info.key);
   if (!info.main || info.key.startsWith('DIALOG')) continue;
   if (info.st === 'none' || info.w < 2) problems.push(`${info.key}: outline ${info.st} ${info.w}px`);
   else if (info.color !== 'rgb(31, 107, 71)') problems.push(`${info.key}: outline colour ${info.color}`);
   else if (info.ring < 3) problems.push(`${info.key}: ring ${info.ring.toFixed(2)}:1`);
  }
  expect(seen.size).toBeGreaterThan(0);
  expect(problems).toEqual([]);
 });

 test(`kontrast besedila 4.5:1 in vsebina brez vodoravnega drsenja pri 320px: ${name}`, async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await setup(page); await settle(page);
  const out = await page.evaluate(() => {
   const { visible, rgba, bg, ratio } = window.__a, problems: string[] = [];
   if (document.documentElement.scrollWidth > innerWidth + 1) problems.push(`page scrolls sideways ${document.documentElement.scrollWidth} > ${innerWidth}`);
   for (const el of document.querySelectorAll('main *, dialog *')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > innerWidth + 1 && !el.closest('.sr-only') && getComputedStyle(el).position !== 'absolute') problems.push(`overflows right edge: <${el.tagName.toLowerCase()}> "${(el.textContent ?? '').trim().slice(0, 30)}" ${r.right.toFixed(0)}`);
    const own = [...el.childNodes].some(n => n.nodeType === Node.TEXT_NODE && (n.textContent ?? '').trim());
    if (!own || el.closest(':disabled')) continue;
    const s = getComputedStyle(el), ground = bg(el), fg = rgba(s.color), c = ratio([0, 1, 2].map(i => fg[i] * fg[3] + ground[i] * (1 - fg[3])), ground);
    const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && +s.fontWeight >= 700);
    if (c < (large ? 3 : 4.5)) problems.push(`contrast ${c.toFixed(2)} on "${(el.textContent ?? '').trim().slice(0, 30)}"`);
   }
   return [...new Set(problems)];
  });
  expect(out).toEqual([]);
 });
}

// ---------------------------------------------------------------- Drawer: trap, Escape, focus return
for (const button of OPENERS) {
 test(`Drawer "${button}": fokus je v panelu in Tab/Shift+Tab ne uide na stran za njim`, async ({ page }) => {
  await itemsScreen(page);
  await page.getByRole('button', { name: button }).focus(); await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await settle(page);
  // Native modal <dialog>: focus cycles through the dialog and the browser UI (document.body); it never reaches the page behind.
  const contained = () => page.evaluate(() => { const el = document.activeElement; return el === document.body || !!el?.closest('dialog'); });
  expect(await page.evaluate(() => !!document.activeElement?.closest('dialog')), 'initial focus inside the dialog').toBe(true);
  for (let i = 0; i < 14; i++) { await page.keyboard.press('Tab'); expect(await contained(), `Tab ${i + 1} reached the page behind the dialog`).toBe(true); }
  for (let i = 0; i < 14; i++) { await page.keyboard.press('Shift+Tab'); expect(await contained(), `Shift+Tab ${i + 1} reached the page behind the dialog`).toBe(true); }
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
 });
}

test('[A11Y-13] Escape vrne fokus na gumb, ki je odprl panel (2.4.3)', async ({ page }) => {
 await itemsScreen(page);
 for (const name of OPENERS) {
  const opener = page.getByRole('button', { name });
  await opener.focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(opener, name).toBeFocused();
 }
});

test('[A11Y-13b] gumb Zapri vrne fokus na gumb, ki je odprl panel (2.4.3)', async ({ page }) => {
 await itemsScreen(page);
 const opener = page.getByRole('button', { name: 'Nova postavka' });
 await opener.click(); await page.getByRole('dialog').getByRole('button', { name: 'Zapri' }).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await expect(opener).toBeFocused();
});

test('[A11Y-13c] uspešno shranjena postavka zapre panel in vrne fokus na sprožilec (2.4.3)', async ({ page }) => {
 await itemsScreen(page);
 await page.route('**/api/podjetja/*/projekti/*/postavke', r => r.request().method() === 'POST' ? r.fulfill({ status: 201, json: {} }) : r.fallback());
 const opener = page.getByRole('button', { name: 'Nova postavka' });
 await opener.click();
 const d = await fillItem(page);
 await d.getByRole('button', { name: 'Shrani postavko' }).click();
 await expect(d).toHaveCount(0);
 await expect(opener).toBeFocused();
});

test('[A11Y-13d] dodana izmera ne zapre panela in fokus ostane v njem (2.4.3)', async ({ page }) => {
 await itemsScreen(page);
 await page.route('**/api/podjetja/*/projekti/*/postavke/i2/izmere', r => r.request().method() === 'POST' ? r.fulfill({ status: 201, json: {} }) : r.fallback());
 await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
 const d = page.getByRole('dialog'); await d.getByLabel('Dolžina').fill('3'); await d.getByLabel('Višina').fill('2');
 const saved = page.waitForResponse(r => r.url().endsWith('/postavke/i2/izmere') && r.request().method() === 'POST');
 await d.getByRole('button', { name: 'Dodaj izmero' }).click(); await saved; await settle(page);
 await expect(d).toBeVisible();
 expect(await page.evaluate(() => !!document.activeElement?.closest('dialog') && document.activeElement?.tagName !== 'BODY'), 'focus stays inside the izmere panel').toBe(true);
});

test('[A11Y-02] izbira postavke cenika prestavi fokus v polje Količina, vrnitev na seznam ne izgubi fokusa (2.4.3)', async ({ page }) => {
 await itemsScreen(page);
 await page.getByRole('button', { name: 'Dodaj iz cenika' }).click();
 const d = page.getByRole('dialog');
 await d.getByRole('button', { name: 'Izberi Polaganje keramike' }).focus(); await page.keyboard.press('Enter');
 await expect(d.getByLabel('Količina')).toBeFocused(); // autoFocus works for the step forward
 const back = d.getByRole('button', { name: 'Izberi drugo postavko' });
 if (!await back.count()) return; // the step back is optional in the project items picker
 await back.focus(); await page.keyboard.press('Enter');
 await expect(d.getByRole('table')).toBeVisible();
 const focus = await page.evaluate(() => { const el = document.activeElement; return { body: el === document.body, dialog: el?.tagName === 'DIALOG', inside: !!el?.closest('dialog') && el?.tagName !== 'DIALOG' }; });
 expect(focus, 'focus after going back to the list').toMatchObject({ body: false, inside: true });
});

test('vrstni red tabulatorja v osnutku ponudbe je logičen: predogled nima gumbov vrstic, pošiljanje je dosegljivo', async ({ page }) => {
 await masterQuote(page);
 await page.getByRole('main').getByRole('heading', { name: /P-2026-001/ }).evaluate(el => { el.setAttribute('tabindex', '-1'); (el as HTMLElement).focus(); });
 const order: string[] = [];
 for (let i = 0; i < 6; i++) { await page.keyboard.press('Tab'); order.push(await page.evaluate(() => { const el = document.activeElement!; return el.closest('main') ? (el.getAttribute('aria-label') ?? el.textContent ?? '').trim() : ''; })); }
 const reached = order.filter(Boolean);
 expect(reached).toContain('Pošlji stranki'); expect(reached.filter(n => /^(Uredi|Odstrani|Izmere) (Rušenje|Polaganje|Montaža)/.test(n) || ['Dodaj iz cenika', 'Ročni vnos'].includes(n))).toEqual([]);
});

test('vrstni red tabulatorja na postavkah projekta: dejanja seznama, nato gumbi prve in druge vrstice', async ({ page }) => {
 await itemsScreen(page);
 await page.getByRole('main').getByRole('heading', { level: 1, name: 'Obnova kopalnice' }).evaluate(el => { el.setAttribute('tabindex', '-1'); (el as HTMLElement).focus(); });
 const order: string[] = [];
 for (let i = 0; i < 14; i++) { await page.keyboard.press('Tab'); order.push(await page.evaluate(() => { const el = document.activeElement!; return el.closest('main') ? (el.getAttribute('aria-label') ?? el.textContent ?? '').trim() : ''; })); }
 const at = (name: string) => order.indexOf(name);
 const head = ['Nova postavka', 'Dodaj iz cenika'].map(at), first = ['Izmere Rušenje estriha', 'Uredi Rušenje estriha', 'Odstrani Rušenje estriha'].map(at), second = ['Izmere Polaganje keramike', 'Uredi Polaganje keramike', 'Odstrani Polaganje keramike'].map(at);
 for (const i of [...head, ...first, ...second]) expect(i, JSON.stringify(order)).toBeGreaterThanOrEqual(0);
 expect(Math.max(...head), 'list actions come before the row buttons').toBeLessThan(Math.min(...first));
 expect(Math.max(...first), 'first row before second row').toBeLessThan(Math.min(...second));
});

// ---------------------------------------------------------------- focus after a control disappears
test('[A11Y-03] po "Pošlji stranki" fokus ne pade na body (2.4.3)', async ({ page }) => {
 await masterQuote(page);
 let sent = false;
 await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', r => { sent = true; return r.fulfill({ json: quoteFull('poslana') }); });
 await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1', r => r.fulfill({ json: quoteFull(sent ? 'poslana' : 'osnutek') }));
 await page.getByRole('button', { name: 'Pošlji stranki' }).focus(); await page.keyboard.press('Enter');
 await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
 await expect(page.getByRole('button', { name: 'Pripravi novo različico' })).toBeVisible();
 expect(await page.evaluate(() => document.activeElement === document.body), 'focus reset to <body>').toBe(false);
});

test('[A11Y-01] sprejem ponudbe: fokus preide v potrditev in potrditev je objavljena (2.4.3, 4.1.3)', async ({ page }) => {
 await customer(page);
 await page.getByRole('button', { name: 'Sprejmi ponudbo' }).focus(); await page.keyboard.press('Enter');
 const group = page.getByRole('group', { name: 'Potrditev odločitve' });
 await expect(group).toBeVisible();
 expect(await page.evaluate(() => !!document.activeElement?.closest('[aria-label="Potrditev odločitve"]')), 'focus moved into the confirmation group').toBe(true);
});

test('[A11Y-01b] preklic potrditve vrne fokus na gumb Sprejmi ponudbo (2.4.3)', async ({ page }) => {
 await customer(page);
 await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
 await page.getByRole('button', { name: 'Prekliči' }).focus(); await page.keyboard.press('Enter');
 await expect(page.getByRole('button', { name: 'Sprejmi ponudbo' })).toBeFocused();
});

test('[A11Y-05] rezultat odločitve stranke je objavljen v živi regiji (4.1.3)', async ({ page }) => {
 await customer(page);
 let accepted = false;
 await page.route('**/api/projekti/*/ponudbe/*/odlocitev', r => { accepted = true; return r.fulfill({ json: customerQuote('sprejeta') }); });
 await page.route('**/api/projekti/*/ponudbe', r => r.fulfill({ json: [customerQuote(accepted ? 'sprejeta' : 'poslana')] }));
 await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
 await page.getByRole('button', { name: 'Potrdi sprejem' }).click();
 await expect(page.getByRole('button', { name: 'Zavrni ponudbo' })).toHaveCount(0);
 const live = page.locator('[role=status], [role=alert], [aria-live]:not([aria-live=off])').filter({ hasText: /sprejet/i });
 await expect(live, 'accepted outcome in a live region').toHaveCount(1);
});

test('napaka pri odločitvi stranke je v role=alert in fokus ostane v skupini', async ({ page }) => {
 await customer(page);
 await page.route('**/api/projekti/*/ponudbe/*/odlocitev', r => r.fulfill({ status: 409, json: { detail: 'Ponudba je že zaključena.' } }));
 await page.getByRole('button', { name: 'Zavrni ponudbo' }).click();
 await page.getByRole('button', { name: 'Potrdi zavrnitev' }).click();
 await expect(page.getByRole('alert')).toContainText('Ponudba je že zaključena.');
});

test('napaka pri pošiljanju ponudbe je v role=alert', async ({ page }) => {
 await masterQuote(page);
 await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', r => r.fulfill({ status: 409, json: { detail: 'Ponudba ni več osnutek.' } }));
 await page.getByRole('button', { name: 'Pošlji stranki' }).click();
 await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
 await expect(page.getByRole('alert')).toContainText('Ponudba ni več osnutek.');
});

test('napaka pri shranjevanju postavke je v role=alert znotraj panela, panel ostane odprt', async ({ page }) => {
 await itemsScreen(page);
 await page.route('**/api/podjetja/*/projekti/*/postavke', r => r.request().method() === 'POST' ? r.fulfill({ status: 422, json: { detail: 'Vnos ni veljaven.' } }) : r.fallback());
 await page.getByRole('button', { name: 'Nova postavka' }).click();
 const d = await fillItem(page);
 await d.getByRole('button', { name: 'Shrani postavko' }).click();
 await expect(d.getByRole('alert')).toContainText('Vnos ni veljaven.');
 await expect(d).toBeVisible();
});

test('napaka pri dodajanju izmere je v role=alert znotraj panela', async ({ page }) => {
 await itemsScreen(page);
 await page.route('**/api/podjetja/*/projekti/*/postavke/i2/izmere', r => r.request().method() === 'POST' ? r.fulfill({ status: 409, json: { detail: 'Izmere bi dale negativno količino.' } }) : r.fallback());
 await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
 const d = page.getByRole('dialog'); await d.getByLabel('Dolžina').fill('1'); await d.getByLabel('Višina').fill('1'); await d.getByRole('button', { name: 'Dodaj izmero' }).click();
 await expect(d.getByRole('alert')).toContainText('Izmere bi dale negativno količino.');
});

test('[A11Y-06] shranjen termin je objavljen v živi regiji (4.1.3)', async ({ page }) => {
 await progress(page, 'termin');
 await page.getByLabel('Začetek termina').fill('2026-11-20T08:00'); await page.getByLabel('Konec termina').fill('2026-11-21T16:00');
 await page.getByRole('button', { name: 'Potrdi termin' }).click();
 await expect(page.getByLabel('Začetek termina')).toHaveValue(/2026-11-1[0-9]|2026-11-20/); // form re-renders with the saved value
 await expect(page.locator('[role=status]').filter({ hasText: /termin/i }), 'success message in role=status').toHaveCount(1);
});

test('napaka obrazca za termin je v role=alert', async ({ page }) => {
 await progress(page, 'termin');
 await page.getByLabel('Začetek termina').fill('2026-11-21T08:00'); await page.getByLabel('Konec termina').fill('2026-11-20T08:00');
 await page.getByRole('button', { name: 'Potrdi termin' }).click();
 await expect(page.getByRole('alert')).toHaveText('Konec termina mora biti po začetku.');
});

test('[A11Y-03b] po "Evidentiraj plačilo" fokus ne pade na body (2.4.3)', async ({ page }) => {
 await invoicePanel(page, 'izdan');
 await page.getByRole('button', { name: 'Evidentiraj plačilo' }).focus(); await page.keyboard.press('Enter');
 await expect(page.getByText('Plačan').first()).toBeVisible();
 expect(await page.evaluate(() => document.activeElement === document.body), 'focus reset to <body>').toBe(false);
});

test('[A11Y-03c] po "Izdaj račun" fokus ne pade na body (2.4.3)', async ({ page }) => {
 await invoicePanel(page, 'osnutek-pripravljen');
 await page.getByRole('button', { name: 'Izdaj račun' }).focus(); await page.keyboard.press('Enter');
 await page.getByRole('button', { name: 'Potrdi izdajo' }).click();
 await expect(page.getByRole('button', { name: 'Evidentiraj plačilo' })).toBeVisible();
 expect(await page.evaluate(() => document.activeElement === document.body), 'focus reset to <body>').toBe(false);
});

test('[A11Y-07] nepovratni izdaji računa in pošiljanju ponudbe je potrebna potrditev (3.3.4)', async ({ page }) => {
 await invoicePanel(page, 'osnutek-pripravljen');
 let posted = false;
 page.on('request', r => { if (r.method() === 'POST' && r.url().endsWith('/racun/izdaj')) posted = true; });
 await page.getByRole('button', { name: 'Izdaj račun' }).click();
 await expect(page.getByRole('button', { name: 'Potrdi izdajo' }), 'confirmation step exists').toBeVisible();
 await page.waitForTimeout(400);
 expect(posted, 'issuing an immutable invoice fired before confirmation').toBe(false);
 await page.getByRole('button', { name: 'Potrdi izdajo' }).click();
 await expect.poll(() => posted).toBe(true);
});

test('[A11Y-07b] pošiljanje ponudbe zahteva potrditev (3.3.4)', async ({ page }) => {
 await masterQuote(page);
 let posted = false;
 await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', r => { posted = true; return r.fulfill({ json: quoteFull('poslana') }); });
 await page.getByRole('button', { name: 'Pošlji stranki' }).click();
 await expect(page.getByRole('button', { name: 'Potrdi pošiljanje' }), 'confirmation step exists').toBeVisible();
 await page.waitForTimeout(400);
 expect(posted, 'sending an immutable quote fired before confirmation').toBe(false);
 await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
 await expect.poll(() => posted).toBe(true);
});

test('[A11Y-08] odpiranje in vrnitev iz podrobnosti ne izgubita fokusa (2.4.3)', async ({ page }) => {
 await mockApi(page, {}); await signIn(page); await open(page, 'projekti');
 const opener = page.getByRole('button', { name: 'Več dejanj Nov estrih' });
 await opener.focus(); await page.keyboard.press('Enter');
 const item = page.getByRole('menuitem', { name: 'Izvedba', exact: true }); await expect(item).toBeFocused().catch(() => item.focus()); await page.keyboard.press('Enter');
 await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible();
 expect(await page.evaluate(() => document.activeElement === document.body), 'focus after opening the detail').toBe(false);
 await page.getByRole('button', { name: 'Nazaj na projekte' }).focus(); await page.keyboard.press('Enter');
 await expect(page.getByRole('heading', { level: 1, name: 'Projekti' })).toBeVisible();
 expect(await page.evaluate(() => document.activeElement === document.body), 'focus after returning to the list').toBe(false);
});

// ---------------------------------------------------------------- tables on the phone
async function axCounts(page: Page, tableName: string) {
 const cdp = await page.context().newCDPSession(page);
 const { nodes } = await cdp.send('Accessibility.getFullAXTree') as { nodes: { nodeId: string; role?: { value: string }; name?: { value: string }; childIds?: string[]; ignored?: boolean }[] };
 const byId = new Map(nodes.map(n => [n.nodeId, n]));
 const table = nodes.find(n => n.role?.value === 'table' && !!n.name?.value?.startsWith(tableName));
 if (!table) return null;
 const counts: Record<string, number> = {};
 const walk = (n: typeof table) => { for (const id of n.childIds ?? []) { const c = byId.get(id); if (!c) continue; const role = c.role?.value ?? ''; counts[role] = (counts[role] ?? 0) + 1; walk(c); } };
 walk(table);
 return counts;
}
test('[A11Y-09] tabela postavk ohrani semantiko tabele tudi v kartični razporeditvi (1.3.1)', async ({ page }) => {
 await masterQuote(page, 'poslana');
 const counts = await axCounts(page, 'Postavke ponudbe P-2026-001');
 expect(counts, 'table role exposed in the accessibility tree').not.toBeNull();
 expect(counts!.row).toBe(3); expect(counts!.columnheader).toBeGreaterThanOrEqual(5); expect(counts!.cell).toBe(2 * counts!.columnheader);
});

test('[A11Y-09c] tabela postavk projekta ohrani semantiko tabele (1.3.1)', async ({ page }) => {
 await itemsScreen(page);
 const counts = await axCounts(page, 'Postavke projekta');
 expect(counts, 'table role exposed in the accessibility tree').not.toBeNull();
 expect(counts!.row).toBe(4); expect(counts!.columnheader).toBeGreaterThanOrEqual(5);
});

test('[A11Y-09b] tabela projektov stranke ohrani semantiko tabele (1.3.1)', async ({ page }) => {
 await mockApi(page, {}); await signIn(page); await open(page, 'moji');
 const counts = await axCounts(page, 'Moji projekti');
 expect(counts, 'table role exposed in the accessibility tree').not.toBeNull();
 expect(counts).toMatchObject({ row: 5, columnheader: 5 });
});

test('[A11Y-10] v kartični razporeditvi ima vsaka vrednost viden naziv stolpca (1.3.1, 3.3.2)', async ({ page }) => {
 test.skip(!phone(page), 'card layout only below 640px');
 await masterQuote(page, 'poslana');
 const unlabeled = await page.evaluate(() => [...document.querySelectorAll('table.data-table tbody tr')].flatMap(tr => [...tr.children].slice(1).filter(td => td.hasAttribute('data-label'))
  .filter(td => !/./.test(getComputedStyle(td, '::before').content.replace(/^"|"$/g, '').replace(/^none$|^normal$/, ''))).map(td => `${td.getAttribute('data-label')}: ${td.textContent}`)));
 expect(unlabeled, 'cells whose column name is not shown in the card').toEqual([]);
});

// ---------------------------------------------------------------- colour alone, tooltip, motion
test('[A11Y-11] pretekle in prihodnje faze projekta se razlikujejo tudi brez barve (1.4.1)', async ({ page }) => {
 await progress(page, 'izvedba');
 const items = page.getByRole('list', { name: 'Faze projekta' }).getByRole('listitem');
 const sig = (n: number) => items.nth(n).evaluate(li => { const b = li.querySelector('.status-badge')!, s = getComputedStyle(b); return { sr: li.querySelector('.sr-only')?.textContent ?? '', svg: !!li.querySelector('svg'), shadow: s.boxShadow, weight: s.fontWeight, decoration: s.textDecorationLine, border: s.borderTopWidth, cur: li.getAttribute('aria-current') }; });
 const [past, future] = [await sig(0), await sig((await items.count()) - 1)];
 // done vs. todo must differ by text, icon or shape, not only by background colour
 expect({ ...past, cur: null }, 'past phase differs from a future phase only by colour').not.toEqual({ ...future, cur: null });
});

test('status računa in ponudbe nosi besedilo, ne le barve', async ({ page }) => {
 await invoicePanel(page, 'izdan');
 await expect(page.locator('.status-badge', { hasText: 'Neplačan' })).toBeVisible();
 await page.getByRole('button', { name: 'Nazaj na projekte' }).click();
});

test('[A11Y-12] namig ikone je mogoče skriti z Escape (1.4.13)', async ({ page }) => {
 await mockApi(page, {}); await signIn(page); await open(page, 'projekti');
 const button = page.getByRole('button', { name: 'Več dejanj Nov estrih' });
 await page.getByRole('main').getByRole('heading', { level: 1 }).evaluate(el => { el.setAttribute('tabindex', '-1'); (el as HTMLElement).focus(); });
 for (let i = 0; i < 40 && !(await button.evaluate(el => el === document.activeElement)); i++) await page.keyboard.press('Tab');
 await expect(button).toBeFocused();
 const opacity = () => button.evaluate(el => getComputedStyle(el, '::after').opacity);
 await expect.poll(opacity, { message: 'tooltip shown on keyboard focus' }).toBe('1');
 await page.keyboard.press('Escape');
 await page.waitForTimeout(400);
 expect(await opacity(), 'tooltip still visible after Escape').toBe('0');
});

test('prefers-reduced-motion odstrani animacije panela in obvestil', async ({ page }) => {
 await page.emulateMedia({ reducedMotion: 'reduce' });
 await itemsScreen(page);
 await page.getByRole('button', { name: 'Dodaj iz cenika' }).click();
 const res = await page.getByRole('dialog').evaluate(el => ({ dialog: getComputedStyle(el).animationName, backdrop: getComputedStyle(el, '::backdrop').animationName, btn: getComputedStyle(el.querySelector('button')!).transitionDuration }));
 expect(res).toEqual({ dialog: 'none', backdrop: 'none', btn: '0s' });
});

test('brez prefers-reduced-motion panel drsi (kontrolni test)', async ({ page }) => {
 await page.emulateMedia({ reducedMotion: 'no-preference' });
 await itemsScreen(page);
 await page.getByRole('button', { name: 'Dodaj iz cenika' }).click();
 expect(await page.getByRole('dialog').evaluate(el => getComputedStyle(el).animationName)).toBe('drawer-in');
});
