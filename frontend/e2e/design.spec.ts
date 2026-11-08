import { expect, test, type Page } from '@playwright/test';
import { mockApi, mockFlow, signIn, type Mock } from './fixtures';
import { layoutProblems, rowAction } from './layout';

// The visual system as measurable rules (docs/razvoj/frontend-arhitektura.md, "Vizualni sistem").
// Every screen is checked at desktop and phone width and saved for review in test-results/screens/.
type Screen = 'pregled' | 'cenik' | 'vrste' | 'zaloge' | 'materiali' | 'admin' | 'prosnja' | 'projekti' | 'moji' | 'delavci';
const nav: Record<Exclude<Screen, 'pregled'>, string> = { cenik: 'Cenik', vrste: 'Vrste dela', zaloge: 'Zaloge', materiali: 'Materiali', admin: 'Podjetja in pravice', prosnja: 'Prošnja za mojstra', projekti: 'Projekti', moji: 'Moji projekti', delavci: 'Delavci' };
const phone = (page: Page) => page.viewportSize()!.width < 800;

async function open(page: Page, screen: Screen) {
 await page.goto('/');
 await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
 if (screen === 'pregled') return;
 if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
 await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: nav[screen], exact: true }).click();
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
 expect.soft(await layoutProblems(page), 'layout').toEqual([]);
 expect(await audit(page)).toEqual([]);
}

test.describe('Prijavljen mojster in admin', () => {
 test.beforeEach(async ({ page }) => { await mockApi(page); await signIn(page); });
 for (const screen of ['pregled', 'cenik', 'vrste', 'zaloge', 'materiali', 'admin', 'prosnja', 'projekti', 'moji', 'delavci'] as const) {
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
  await page.getByRole('tab', { name: /^Prošnje mojstrov/ }).click();
  await expect(page.getByRole('tabpanel')).toBeVisible();
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

 test('vrste dela: seznam z ceno dela, materiali vrste v predalu, v ceniku ni več sestave', async ({ page }, info) => {
  await open(page, 'vrste');
  await expect(page.getByRole('row', { name: /Keramika/ })).toContainText(/400,00\s?€/); await expect(page.getByRole('row', { name: /Rušenje/ })).toContainText(/0,00\s?€/);
  await expect(page.getByRole('row', { name: /Staro delo/ })).toContainText('Neaktivna');
  await page.getByRole('button', { name: 'Materiali Keramika' }).click();
  const panel = page.getByRole('dialog');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Lepilo za ploščice · 4,5 kg na enoto')).toBeVisible();
  await expect(panel.getByText('Cement · 1,2 kg na enoto')).toBeVisible();
  await expect(panel.getByLabel('Material')).toBeVisible(); await expect(panel.getByLabel('Količina na enoto')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Dodaj material' })).toBeVisible(); await expect(panel.getByRole('button', { name: 'Odstrani Cement' })).toBeVisible();
  await check(page, 'vrsta-dela-materiali', info.project.name);
  await page.keyboard.press('Escape'); await page.getByRole('button', { name: 'Nova vrsta dela' }).click();
  for (const label of ['Naziv', 'Opis', 'Urna postavka (€)', 'Število ur', 'Število delavcev']) await expect(page.getByRole('dialog').getByLabel(label)).toBeVisible();
  await check(page, 'vrsta-dela-obrazec', info.project.name);
 });

 test('cenik kaže vrsto dela in enoto, postavka nima več materialne sestave', async ({ page }, info) => {
  await open(page, 'cenik');
  await expect(page.getByRole('main').getByText('Keramika · m2').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Materialna sestava/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Uredi Polaganje keramike' }).click();
  const d = page.getByRole('dialog'); await expect(d.getByLabel('Vrsta dela')).toHaveValue('v1'); await expect(d.getByLabel('Vrsta dela')).toHaveAttribute('required', '');
  await expect(d.getByLabel('Enota')).toHaveValue('m2');
  await check(page, 'cenik-obrazec-vrsta', info.project.name);
 });

 test('projekti mojstra so združeni po fazah z obrazcem za nov projekt', async ({ page }, info) => {
  await open(page, 'projekti');
  for (const phase of ['Pregled', 'Ponudba', 'Izvedba']) await expect(page.getByRole('heading', { name: phase })).toBeVisible();
  await expect(page.getByText('Menjava oken')).toBeVisible();
  await page.getByRole('button', { name: 'Več dejanj Obnova kopalnice' }).click();
  await expect(page.getByRole('menuitem', { name: 'Zahtevaj ogled' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Več dejanj Menjava oken' }).click();
  await expect(page.getByRole('menuitem', { name: 'Zahtevaj ogled' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  for (const label of ['E-pošta stranke', 'Naziv', 'Lokacija izvedbe', 'Opis']) await expect(page.getByLabel(label)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ustvari projekt' })).toBeVisible();
  await check(page, 'projekti', info.project.name);
 });

 test('stranka vidi svoje projekte samo za branje', async ({ page }, info) => {
  await open(page, 'moji');
  await expect(page.getByText('Beljenje stanovanja')).toBeVisible();
  await expect(page.getByText('Gradnje Kos d.o.o.').first()).toBeVisible();
  await expect(page.getByText('Kranj, Trg 3')).toBeVisible();
  await expect(page.getByRole('button', { name: /^(Uredi|Zahtevaj ogled)/ })).toHaveCount(0);
  await check(page, 'moji-projekti', info.project.name);
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

test.describe('Osnutek ponudbe', () => {
 async function editor(page: Page, quote: 'osnutek' | 'prazen' | 'poslana' | 'brez') {
  await mockApi(page, { quote }); await signIn(page);
  await open(page, 'projekti');
  await rowAction(page, 'Obnova kopalnice', 'Ponudba');
 }

 test('osnutek s postavkami pokaže številko, postavke in vsote', async ({ page }, info) => {
  await editor(page, 'osnutek');
  await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
  for (const text of ['Rušenje estriha', 'Polaganje keramike']) await expect(page.getByText(text).first()).toBeVisible();
  const totals = page.getByRole('group', { name: 'Vsote ponudbe' });
  for (const amount of [/990,00\s?€/, /217,80\s?€/, /1\.?207,80\s?€/]) await expect(totals).toContainText(amount);
  await expect(page.getByRole('row', { name: /Rušenje estriha/ })).toContainText(/45\s?m²/);
  for (const name of ['Dodaj iz cenika', 'Ročni vnos', 'Uredi Rušenje estriha', 'Odstrani Rušenje estriha']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeEnabled();
  await check(page, 'ponudba-osnutek', info.project.name);
 });

 test('osnutek brez postavk ima onemogočeno pošiljanje', async ({ page }, info) => {
  await editor(page, 'prazen');
  await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeDisabled();
  await check(page, 'ponudba-prazna', info.project.name);
 });

 test('projekt brez ponudbe ponuja ustvaritev osnutka', async ({ page }, info) => {
  await editor(page, 'brez');
  await expect(page.getByRole('button', { name: 'Ustvari osnutek ponudbe' })).toBeVisible();
  await check(page, 'ponudba-brez', info.project.name);
 });

 test('poslana ponudba je samo za branje s ponudbo nove različice', async ({ page }, info) => {
  await editor(page, 'poslana');
  await expect(page.getByRole('button', { name: 'Pripravi novo različico' })).toBeVisible();
  for (const name of ['Dodaj iz cenika', 'Ročni vnos', 'Pošlji stranki']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await check(page, 'ponudba-poslana', info.project.name);
 });

 test('osnutek je predogled: postavke se urejajo na projektu', async ({ page }, info) => {
  await editor(page, 'osnutek');
  await expect(page.getByRole('button', { name: /^(Uredi|Odstrani|Izmere) (Rušenje|Polaganje|Montaža)/ })).toHaveCount(0);
  await check(page, 'ponudba-predogled', info.project.name);
 });
});

test.describe('Dodajanje iz cenika na projektu', () => {
 test('predal ponuja aktivne postavke cenika, neaktivne ne', async ({ page }, info) => {
  await mockApi(page); await signIn(page); await open(page, 'projekti');
  await rowAction(page, 'Obnova kopalnice', 'Postavke');
  await page.getByRole('button', { name: 'Dodaj iz cenika' }).click();
  const panel = page.getByRole('dialog');
  await expect(panel.getByText('Polaganje keramike')).toBeVisible();
  await expect(panel.getByText('Zaključno čiščenje')).toHaveCount(0);
  await check(page, 'postavke-cenik-panel', info.project.name);
 });
});

test.describe('Ponudba za stranko', () => {
 async function customerQuote(page: Page, state: 'poslana' | 'sprejeta') {
  await mockApi(page, { customerQuote: state }); await signIn(page);
  await open(page, 'moji');
  await page.getByRole('button', { name: 'Ponudba Menjava oken' }).click();
  await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
 }

 test('poslana ponudba pokaže postavke, vsote ter sprejem in zavrnitev', async ({ page }, info) => {
  await customerQuote(page, 'poslana');
  for (const text of ['Rušenje estriha', 'Polaganje keramike']) await expect(page.getByText(text).first()).toBeVisible();
  const totals = page.getByRole('group', { name: 'Vsote ponudbe' });
  for (const amount of [/990,00\s?€/, /217,80\s?€/, /1\.?207,80\s?€/]) await expect(totals).toContainText(amount);
  await expect(page.getByRole('main').getByText(/Material/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Sprejmi ponudbo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zavrni ponudbo' })).toBeVisible();
  await check(page, 'ponudba-stranka-poslana', info.project.name);
 });

 test('sprejem zahteva potrditev', async ({ page }, info) => {
  await customerQuote(page, 'poslana');
  await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
  await expect(page.getByRole('button', { name: 'Potrdi sprejem' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Prekliči' })).toBeVisible();
  await check(page, 'ponudba-stranka-potrditev', info.project.name);
 });

 test('sprejeta ponudba nima več gumbov za odločitev', async ({ page }, info) => {
  await customerQuote(page, 'sprejeta');
  await expect(page.getByText('Sprejeta').first()).toBeVisible();
  for (const name of ['Sprejmi ponudbo', 'Zavrni ponudbo']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await check(page, 'ponudba-stranka-sprejeta', info.project.name);
 });
});

test.describe('Termin in izvedba', () => {
 async function progress(page: Page, options: Mock) {
  await mockApi(page, options); await signIn(page);
  await open(page, 'projekti');
  await rowAction(page, 'Nov estrih', 'Izvedba');
  await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible();
 }

 test('faza termin ponudi obrazec za termin brez zaključka izvedbe', async ({ page }, info) => {
  await progress(page, { progress: 'termin' });
  await expect(page.getByRole('list', { name: 'Faze projekta' }).getByRole('listitem')).toHaveCount(7);
  await expect(page.getByLabel('Začetek termina')).toBeVisible(); await expect(page.getByLabel('Konec termina')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Potrdi termin' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zaključi izvedbo' })).toHaveCount(0);
  await check(page, 'potek-termin', info.project.name);
 });

 test('izvedba pokaže predizpolnjen termin in gumb Zaključi izvedbo', async ({ page }, info) => {
  await progress(page, { progress: 'izvedba' });
  await expect(page.getByRole('listitem').filter({ hasText: 'Izvedba' }).and(page.locator('[aria-current="step"]'))).toBeVisible();
  await expect(page.getByLabel('Začetek termina')).not.toHaveValue('');
  await expect(page.getByRole('button', { name: 'Zaključi izvedbo' })).toBeVisible();
  await check(page, 'potek-izvedba', info.project.name);
 });

 test('zaključena izvedba nima več obrazcev', async ({ page }, info) => {
  await progress(page, { progress: 'koncana' });
  await expect(page.getByText(/Izvedba je zaključena/).first()).toBeVisible();
  for (const name of ['Zaključi izvedbo', 'Potrdi termin']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await check(page, 'potek-koncana', info.project.name);
 });
});

test.describe('Račun', () => {
 async function panel(page: Page, options: Mock) {
  await mockApi(page, options); await signIn(page);
  await open(page, 'projekti');
  await rowAction(page, 'Nov estrih', 'Račun');
  await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible();
 }
 const totals = async (page: Page) => {
  const group = page.getByRole('group', { name: 'Vsote računa' });
  for (const amount of [/990,00\s?€/, /217,80\s?€/, /1\.?207,80\s?€/]) await expect(group).toContainText(amount);
 };

 test('osnutek je pred koncem izvedbe brez možnosti izdaje', async ({ page }, info) => {
  await panel(page, { invoice: 'osnutek' });
  await expect(page.getByRole('heading', { name: /Osnutek računa/ })).toBeVisible(); await totals(page);
  await expect(page.getByRole('button', { name: 'Izdaj račun' })).toBeDisabled();
  await expect(page.getByText(/po zaključeni izvedbi/i).first()).toBeVisible();
  await check(page, 'racun-osnutek', info.project.name);
 });

 test('osnutek po zaključeni izvedbi ima rok plačila in omogoča izdajo', async ({ page }, info) => {
  await panel(page, { invoice: 'osnutek-pripravljen' });
  await expect(page.getByLabel('Rok plačila')).toBeVisible(); await expect(page.getByLabel('Rok plačila')).not.toHaveValue('');
  await expect(page.getByRole('button', { name: 'Izdaj račun' })).toBeEnabled();
  await expect(page.getByLabel('Prejemnik', { exact: true })).toHaveValue('Janez Kranjc'); await expect(page.getByLabel('Naslov prejemnika')).toHaveValue('Ptuj, Slovenska 3');
  await check(page, 'racun-pripravljen', info.project.name);
 });

 test('izdan račun pokaže številko, izdajatelja, prejemnika in gumb za plačilo', async ({ page }, info) => {
  await panel(page, { invoice: 'izdan' });
  await expect(page.getByRole('heading', { name: /R-2026-001/ })).toBeVisible(); await totals(page);
  for (const text of ['Mojster Novak d.o.o.', 'SI12345678', 'Janez Kranjc']) await expect(page.getByRole('main').getByText(text).first()).toBeVisible();
  await expect(page.getByText('Neplačan').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Evidentiraj plačilo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Izdaj račun' })).toHaveCount(0);
  await check(page, 'racun-izdan', info.project.name);
 });

 test('plačan račun je zaključen brez dejanj', async ({ page }, info) => {
  await panel(page, { invoice: 'placan' });
  await expect(page.getByText('Plačan').first()).toBeVisible();
  for (const name of ['Evidentiraj plačilo', 'Izdaj račun']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await check(page, 'racun-placan', info.project.name);
 });

 test('stranka vidi izdan račun brez dejanj', async ({ page }, info) => {
  await mockApi(page, { customerInvoice: 'izdan' }); await signIn(page);
  await open(page, 'moji');
  await expect(page.getByRole('button', { name: 'Račun Menjava oken' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Račun Estrih v kleti' }).click();
  await expect(page.getByRole('heading', { name: /R-2026-001/ })).toBeVisible();
  const group = page.getByRole('group', { name: 'Vsote računa' });
  for (const amount of [/990,00\s?€/, /217,80\s?€/, /1\.?207,80\s?€/]) await expect(group).toContainText(amount);
  for (const text of ['Mojster Novak d.o.o.', 'Janez Kranjc', 'Neplačan']) await expect(page.getByRole('main').getByText(text).first()).toBeVisible();
  for (const name of ['Evidentiraj plačilo', 'Izdaj račun']) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await check(page, 'racun-stranka', info.project.name);
 });

 test('stranka vidi plačan račun', async ({ page }, info) => {
  await mockApi(page, { customerInvoice: 'placan' }); await signIn(page);
  await open(page, 'moji');
  await page.getByRole('button', { name: 'Račun Estrih v kleti' }).click();
  await expect(page.getByText('Plačan').first()).toBeVisible();
  await check(page, 'racun-stranka-placan', info.project.name);
 });
});

// Preoblikovana administracija "Podjetja in pravice" (master-detail) in stran "Delavci" mojstra (US-08), mock API v e2e/fixtures.ts.
test.describe('Podjetja in pravice', () => {
 test.beforeEach(async ({ page }) => { await mockApi(page); await signIn(page); });
 const tab = (page: Page, name: string | RegExp) => page.getByRole('tab', { name });
 const company = async (page: Page, name = /^Mojster Novak d\.o\.o\./) => { await page.getByRole('main').getByRole('button', { name }).first().click(); await expect(page.getByRole('table', { name: /Člani/ })).toBeVisible(); };
 const members = (page: Page) => page.getByRole('table', { name: /Člani/ });
 const notRed = (color: string) => { const [r, g, b] = color.match(/[\d.]+/g)!.map(Number); return !(r > 150 && g < 90 && b < 90); };

 test('štirje zavihki, privzeto Po podjetjih, seznam podjetij in poziv k izbiri', async ({ page }, info) => {
  await open(page, 'admin');
  await expect(page.getByRole('tablist').getByRole('tab')).toHaveText([/^Po podjetjih$/, /^Po uporabnikih$/, /^Prošnje mojstrov/, /^Podjetja$/]);
  await expect(tab(page, 'Po podjetjih')).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Poišči podjetje')).toBeVisible();
  await expect(page.getByRole('main').getByText('2 podjetji')).toBeVisible();
  if (!phone(page)) await expect(page.getByText('Izberite podjetje na levi.')).toBeVisible();
  await check(page, 'admin-po-podjetjih-seznam', info.project.name);
 });

 test('izbrano podjetje pokaže lastnika in aktivne člane, tabela ostane brez vodoravnega drsenja', async ({ page }, info) => {
  await open(page, 'admin'); await company(page);
  await expect(page.getByRole('heading', { name: 'Mojster Novak d.o.o.' })).toBeVisible();
  await expect(page.getByText(/Lastnik: ana@mojster\.example\.test/)).toBeVisible();
  for (const email of ['marko@example.test', 'tina.zupan@example.test', 'ana@mojster.example.test']) await expect(members(page).getByText(email)).toBeVisible();
  await expect(members(page).getByText('peter.horvat@example.test')).toHaveCount(0);
  await expect(page.getByText('3 člani')).toBeVisible();
  if (phone(page)) await expect(page.getByRole('button', { name: /^‹?\s?Podjetja$/ })).toBeVisible();
  await check(page, 'admin-podjetje-clani', info.project.name);
 });

 test('filtra Vloga in Stanje ter iskanje člana spremenijo vrstice in štetje', async ({ page }, info) => {
  await open(page, 'admin'); await company(page);
  await page.getByLabel('Stanje').selectOption({ label: 'Odvzete' });
  await expect(members(page).getByText('peter.horvat@example.test')).toBeVisible(); await expect(members(page).getByText('marko@example.test')).toHaveCount(0); await expect(page.getByText('1 član', { exact: true })).toBeVisible();
  await check(page, 'admin-odvzete', info.project.name);
  await page.getByLabel('Stanje').selectOption({ label: 'Vse' }); await expect(page.getByText('4 člani')).toBeVisible();
  await page.getByLabel('Vloga').selectOption({ label: 'Delavec' }); await expect(page.getByText('3 člani')).toBeVisible();
  await page.getByLabel('Poišči člana').fill('TINA'); await expect(page.getByText('1 član', { exact: true })).toBeVisible();
  await page.getByLabel('Poišči člana').fill('nihče'); await expect(page.getByText('Ni članov, ki ustrezajo filtrom.')).toBeVisible();
  await check(page, 'admin-brez-zadetkov', info.project.name);
  await page.getByRole('button', { name: 'Počisti filtre' }).click(); await expect(members(page).getByText('peter.horvat@example.test')).toBeVisible();
 });

 test('odvzem ima besedilni gumb, ni rdeč, ima velik cilj na telefonu in najprej vpraša', async ({ page }, info) => {
  await open(page, 'admin'); await company(page);
  const revoke = page.getByRole('button', { name: 'Odvzemi vlogo Delavec uporabniku marko@example.test' });
  await expect(revoke).toContainText('Odvzemi');
  const box = (await revoke.boundingBox())!; expect(box.height).toBeGreaterThanOrEqual(phone(page) ? 44 : 28);
  expect(notRed(await revoke.evaluate(el => getComputedStyle(el).backgroundColor))).toBe(true);
  let patched = 0; page.on('request', r => { if (r.method() === 'PATCH') patched++; });
  await revoke.click(); expect(patched).toBe(0);
  await expect(page.getByText('Odvzamem vlogo Delavec uporabniku marko@example.test pri podjetju Mojster Novak d.o.o.?')).toBeVisible();
  await check(page, 'admin-potrditev-odvzema', info.project.name);
  await page.getByRole('button', { name: 'Prekliči' }).click(); expect(patched).toBe(0);
  await revoke.click(); const sent = page.waitForRequest(r => r.method() === 'PATCH' && r.url().endsWith('/admin/vloge/r5'));
  await page.getByRole('button', { name: 'Odvzemi vlogo', exact: true }).click(); expect((await sent).postDataJSON()).toEqual({ aktivna: false });
 });

 test('lastnik ima onemogočen odvzem z vidno razlago', async ({ page }, info) => {
  await open(page, 'admin'); await company(page);
  await expect(page.getByRole('button', { name: /Odvzemi.*ana@mojster\.example\.test/ })).toBeDisabled();
  await expect(page.getByText('Lastnik ne more izgubiti vloge mojster. Najprej zamenjajte lastnika.').first()).toBeVisible();
  await check(page, 'admin-lastnik', info.project.name);
 });

 test('Dodaj člana odpre predal z uporabnikom in vlogo, skrbnik je onemogočen', async ({ page }, info) => {
  await open(page, 'admin'); await company(page);
  await page.getByRole('button', { name: 'Dodaj člana' }).click();
  const d = page.getByRole('dialog'); await expect(d.getByLabel('Uporabnik')).toBeVisible(); await expect(d.getByRole('radio', { name: /Delavec/ })).toBeChecked(); await expect(d.getByRole('radio', { name: /Mojster/ })).toBeVisible();
  await expect(d.getByText('Skrbnik si ne more sam dodeliti vloge v podjetju.')).toBeVisible();
  await check(page, 'admin-predal-dodaj-clana', info.project.name);
 });

 test('Po uporabnikih: vloge uporabnika po podjetjih in povezava v podjetje', async ({ page }, info) => {
  await open(page, 'admin'); await tab(page, 'Po uporabnikih').click();
  await page.getByLabel('Poišči uporabnika').fill('TINA');
  await page.getByRole('main').getByRole('button', { name: /^Tina Zupan/ }).click();
  await expect(page.getByRole('heading', { name: /Tina Zupan/ })).toBeVisible();
  await expect(page.getByRole('group', { name: 'Globalno' })).toContainText('Stranka'); await expect(page.getByRole('group', { name: 'Mojster Novak d.o.o.' })).toContainText('Delavec');
  await expect(page.getByRole('group', { name: 'Gradnje Kos d.o.o.' })).toHaveCount(0);
  await check(page, 'admin-po-uporabnikih', info.project.name);
  await page.getByLabel('Stanje').selectOption({ label: 'Vse' }); await expect(page.getByRole('group', { name: 'Gradnje Kos d.o.o.' }).getByRole('button', { name: /Ponovno aktiviraj/ })).toBeVisible();
  await check(page, 'admin-po-uporabnikih-vse', info.project.name);
  await page.getByRole('button', { name: 'Odpri podjetje Mojster Novak d.o.o.' }).click();
  await expect(tab(page, 'Po podjetjih')).toHaveAttribute('aria-selected', 'true'); await expect(page.getByRole('table', { name: /Člani/ })).toBeVisible();
 });

 test('napaka nalaganja ima opozorilo in Poskusi znova, prazno stanje ostane okvir zaslona', async ({ page }, info) => {
  await mockApi(page, { admin: 'napaka' });
  await open(page, 'admin').catch(() => undefined);
  await expect(page.getByRole('alert')).toContainText('Podatkovna baza trenutno ni na voljo.'); await expect(page.getByRole('button', { name: 'Poskusi znova' })).toBeVisible();
  await check(page, 'admin-napaka', info.project.name);
 });

 test('zavihka Prošnje mojstrov in Podjetja: obrazec podjetja je v predalu', async ({ page }, info) => {
  await open(page, 'admin'); await tab(page, 'Podjetja').click();
  await expect(page.getByLabel('Naziv podjetja')).toHaveCount(0); await page.getByRole('button', { name: 'Dodaj podjetje' }).click();
  await expect(page.getByRole('dialog').getByLabel('Lastnik podjetja')).toBeVisible();
  await check(page, 'admin-podjetja-predal', info.project.name);
 });

 test('mojster vidi v meniju postavko Delavci', async ({ page }) => {
  await page.goto('/'); await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
  await expect(page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: 'Delavci', exact: true })).toBeVisible();
 });
});

test.describe('Delavci mojstra', () => {
 async function workers(page: Page, options: Mock = {}) { await mockApi(page, options); await signIn(page); await open(page, 'delavci'); }

 test('seznam aktivnih delavcev, obrazec po e-pošti in značka Vi', async ({ page }, info) => {
  await workers(page);
  await expect(page.getByText('Sodelavci podjetja Mojster Novak d.o.o.')).toBeVisible();
  await expect(page.getByLabel('E-pošta delavca')).toBeVisible(); await expect(page.getByText('Delavec mora biti že registriran in imeti potrjeno e-pošto.')).toBeVisible();
  const table = page.getByRole('table');
  for (const text of ['Marko Kos', 'marko@example.test', 'Tina Zupan', 'Ana Novak']) await expect(table.getByText(text).first()).toBeVisible();
  await expect(table.getByText('Vi', { exact: true })).toBeVisible(); await expect(table.getByText('Peter Horvat')).toHaveCount(0);
  await expect(page.getByText('3 delavci')).toBeVisible();
  await check(page, 'delavci-seznam', info.project.name);
 });

 test('imenika uporabnikov ni: brez predlogov in brez klicev administracije', async ({ page }) => {
  const seen: string[] = []; page.on('request', r => seen.push(new URL(r.url()).pathname));
  await workers(page); await page.getByLabel('E-pošta delavca').fill('ma');
  await expect(page.locator('datalist')).toHaveCount(0); await expect(page.getByRole('listbox')).toHaveCount(0);
  expect(seen.filter(path => /\/admin\/|uporabniki/.test(path))).toEqual([]);
 });

 test('povabilo: stalno sporočilo, seznam povabil s stanji in preklic s potrditvijo', async ({ page }, info) => {
  await workers(page);
  const section = page.getByRole('table', { name: 'Povabila delavcev' });
  for (const text of ['nina.krajnc@example.test', 'Čaka', 'Zavrnjeno', 'Sprejeto', 'Poteklo', 'Preklicano']) await expect(section.getByText(text, { exact: true })).toBeVisible();
  await expect(section.getByRole('button', { name: /Prekliči povabilo/ })).toHaveCount(1);
  const sent = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith('/delavci/povabila'));
  await page.getByLabel('E-pošta delavca').fill('nekdo@example.test'); await page.getByRole('button', { name: 'Povabi delavca' }).click();
  expect((await sent).postDataJSON()).toEqual({ e_posta: 'nekdo@example.test' });
  await expect(page.getByRole('status').filter({ hasText: 'Povabilo je poslano. Delavec ga mora sprejeti v svojem računu.' })).toBeVisible();
  await check(page, 'delavci-povabilo-poslano', info.project.name);
  await section.getByRole('button', { name: /Prekliči povabilo/ }).click();
  await expect(page.getByText('Prekličem povabilo za nina.krajnc@example.test?')).toBeVisible();
  await check(page, 'delavci-povabilo-preklic', info.project.name);
  const cancelled = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith('/povabila/p1/preklic'));
  await page.getByRole('button', { name: 'Prekliči povabilo', exact: true }).click(); await cancelled;
 });

 test('omejitev povabil pokaže sporočilo strežnika', async ({ page }, info) => {
  await workers(page);
  await page.getByLabel('E-pošta delavca').fill('napaka@example.test'); await page.getByRole('button', { name: 'Povabi delavca' }).click();
  await expect(page.getByRole('alert')).toHaveText('Preveč povabil. Poskusite pozneje.');
  await check(page, 'delavci-povabilo-napaka', info.project.name);
 });

 test('odvzem dostopa vpraša in pove, da druga podjetja ostanejo nespremenjena', async ({ page }, info) => {
  await workers(page);
  const revoke = page.getByRole('button', { name: /Odvzemi dostop.*marko@example\.test/ }); await expect(revoke).toContainText('Odvzemi dostop');
  const box = (await revoke.boundingBox())!; expect(box.height).toBeGreaterThanOrEqual(phone(page) ? 44 : 28);
  let patched = 0; page.on('request', r => { if (r.method() === 'PATCH') patched++; });
  await revoke.click(); expect(patched).toBe(0);
  await expect(page.getByText('Odvzamem dostop delavcu marko@example.test? Njegove vloge pri drugih podjetjih ostanejo nespremenjene.')).toBeVisible();
  await check(page, 'delavci-potrditev', info.project.name);
  const sent = page.waitForRequest(r => r.method() === 'PATCH' && r.url().endsWith('/delavci/w1'));
  await page.getByRole('button', { name: 'Odvzemi dostop', exact: true }).click(); expect((await sent).postDataJSON()).toEqual({ aktivna: false });
 });

 test('odvzeti delavci so za filtrom Odvzeti z gumbom Ponovno omogoči', async ({ page }, info) => {
  await workers(page); await page.getByLabel('Stanje').selectOption({ label: 'Odvzeti' });
  await expect(page.getByRole('button', { name: /Ponovno omogoči.*peter\.horvat@example\.test/ })).toBeVisible(); await expect(page.getByText('Odvzet', { exact: true })).toBeVisible();
  await check(page, 'delavci-odvzeti', info.project.name);
 });

 test('prazno stanje in napaka nalaganja', async ({ page }, info) => {
  await workers(page, { workers: 'prazno' });
  await expect(page.getByText('V podjetju še ni delavcev.')).toBeVisible(); await expect(page.getByText('Povabite prvega delavca z njegovo e-pošto.')).toBeVisible();
  await check(page, 'delavci-prazno', info.project.name);
  await mockApi(page, { workers: 'napaka' }); await page.reload();
  await open(page, 'delavci').catch(() => undefined);
  await expect(page.getByRole('alert')).toContainText('Podatkovna baza trenutno ni na voljo.'); await expect(page.getByRole('button', { name: 'Poskusi znova' })).toBeVisible();
  await check(page, 'delavci-napaka', info.project.name);
 });
});

test.describe('Povabila v podjetja (Pregled)', () => {
 test('kartica s povabilom, sprejem in zavrnitev z vprašanjem', async ({ page }, info) => {
  await mockApi(page, { myInvites: true }); await signIn(page); await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Povabila v podjetja' })).toBeVisible();
  await expect(page.getByText(/vas vabi kot delavca · povabil Boris Kovač/)).toBeVisible();
  await check(page, 'pregled-povabila', info.project.name);
  await page.getByRole('button', { name: 'Zavrni povabilo podjetja Gradnje Kovač d.o.o.' }).click();
  await expect(page.getByText('Zavrnem povabilo podjetja Gradnje Kovač d.o.o.?')).toBeVisible();
  await check(page, 'pregled-povabila-zavrni', info.project.name);
  const sent = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith('/povabila/p1/odlocitev'));
  await page.getByRole('button', { name: 'Zavrni povabilo', exact: true }).click(); expect((await sent).postDataJSON()).toEqual({ sprejmi: false });
 });
});

// Model v3: postavke projekta z vrsto dela, delom in izmerami; stranka vidi samo izmere poslane ponudbe.
test.describe('Postavke projekta in izmere', () => {
 async function items(page: Page, options: Mock = {}) {
  await mockApi(page, options); await signIn(page); await open(page, 'projekti');
  await rowAction(page, 'Obnova kopalnice', 'Postavke');
  await expect(page.getByRole('heading', { level: 1, name: 'Obnova kopalnice' })).toBeVisible();
 }

 test('seznam postavk pokaže vrsto dela, skupno izmero, vsote in označi postavko brez izmer', async ({ page }, info) => {
  await items(page);
  const main = page.getByRole('main');
  for (const text of ['Rušenje estriha', 'Polaganje keramike', 'Keramika']) await expect(main.getByText(text).first()).toBeVisible();
  await expect(page.getByRole('row', { name: /Rušenje estriha/ })).toContainText(/45\s?m²/); await expect(page.getByRole('row', { name: /Polaganje keramike/ })).toContainText(/20\s?m²/);
  await expect(page.getByRole('row', { name: /Montaža vrat/ })).toContainText('Brez izmer');
  const totals = page.getByRole('group', { name: 'Vsote postavk' });
  for (const amount of [/1\.?350,00\s?€/, /297,00\s?€/, /1\.?647,00\s?€/]) await expect(totals).toContainText(amount);
  await check(page, 'postavke-seznam', info.project.name);
 });

 test('prazen projekt ponudi novo postavko, napaka nalaganja ohrani okvir', async ({ page }, info) => {
  await items(page, { items: 'prazno' });
  await expect(page.getByText('Projekt še nima postavk.')).toBeVisible(); await expect(page.getByRole('button', { name: 'Nova postavka' })).toBeVisible();
  await check(page, 'postavke-prazno', info.project.name);
  await mockApi(page, { items: 'napaka' }); await page.reload(); await open(page, 'projekti').catch(() => undefined);
  await rowAction(page, 'Obnova kopalnice', 'Postavke');
  await expect(page.getByRole('alert')).toContainText('Podatkovna baza trenutno ni na voljo.'); await check(page, 'postavke-napaka', info.project.name);
 });

 test('obrazec postavke: vrsta dela je obvezna, delo se prekopira, predogled sledi vnosu', async ({ page }, info) => {
  await items(page); await page.getByRole('button', { name: 'Uredi Polaganje keramike' }).click();
  const d = page.getByRole('dialog');
  for (const label of ['Naziv', 'Opis', 'Vrsta dela', 'Enota', 'Cena na enoto', 'Količina', 'Popust (%)', 'Stopnja DDV (%)', 'Urna postavka (€)', 'Število ur', 'Število delavcev']) await expect(d.getByLabel(label)).toBeVisible();
  await expect(d.getByLabel('Vrsta dela')).toHaveAttribute('required', '');
  const preview = d.getByRole('group', { name: 'Predogled izračuna' });
  for (const amount of [/400,00\s?€/, /540,00\s?€/, /118,80\s?€/, /658,80\s?€/]) await expect(preview).toContainText(amount);
  await d.getByLabel('Popust (%)').fill('0'); await expect(preview).toContainText(/732,00\s?€/);
  await check(page, 'postavka-obrazec', info.project.name);
  await page.keyboard.press('Escape'); await page.getByRole('button', { name: 'Nova postavka' }).click();
  await expect(page.getByRole('dialog').getByLabel('Količina')).toHaveValue('1');
  await page.getByRole('dialog').getByLabel('Vrsta dela').selectOption({ label: 'Keramika' });
  await expect(page.getByRole('dialog').getByLabel('Urna postavka (€)')).toHaveValue(/^25(\.0+)?$/); await expect(page.getByRole('dialog').getByLabel('Število delavcev')).toHaveValue('2');
  await check(page, 'postavka-nova-delo', info.project.name);
 });

 test('izmere m²: dolžina, višina, kosi in odštej, brez širine, s sprotnim izračunom', async ({ page }, info) => {
  await items(page); await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
  const d = page.getByRole('dialog');
  const rows = d.getByRole('listitem'); await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText(/\+\s?20\s?m²/); await expect(rows.nth(2)).toContainText(/−\s?2\s?m²/);
  for (const label of ['Dolžina', 'Višina', 'Kosi']) await expect(d.getByLabel(label)).toBeVisible();
  await expect(d.getByLabel('Širina')).toHaveCount(0); await expect(d.getByRole('checkbox', { name: 'Odštej' })).toBeVisible();
  await d.getByLabel('Dolžina').fill('3'); await d.getByLabel('Višina').fill('2'); await d.getByLabel('Kosi').fill('4');
  await expect(d.getByRole('group', { name: 'Izračun izmere' })).toContainText(/24\s?m²/); await expect(d.getByRole('group', { name: 'Izračun izmere' })).toContainText(/44\s?m²/);
  await check(page, 'izmere-m2', info.project.name);
  await d.getByRole('checkbox', { name: 'Odštej' }).check(); await d.getByLabel('Dolžina').fill('30'); await d.getByLabel('Višina').fill('1');
  await expect(d.getByText('Izmere bi dale negativno količino.')).toBeVisible(); await expect(d.getByRole('button', { name: 'Dodaj izmero' })).toBeDisabled();
  await check(page, 'izmere-negativno', info.project.name);
 });

 test('izmere postavke v kosih imajo samo polje Kosi', async ({ page }) => {
  await items(page);
  await page.getByRole('button', { name: 'Izmere Montaža vrat' }).click();
  const d = page.getByRole('dialog'); await expect(d.getByLabel('Kosi')).toBeVisible(); for (const l of ['Dolžina', 'Višina', 'Širina']) await expect(d.getByLabel(l)).toHaveCount(0);
 });

 test('stranka vidi izmere poslane ponudbe, nikoli dela, ur ali materialov', async ({ page }, info) => {
  await mockApi(page, { customerQuote: 'poslana' }); await signIn(page); await open(page, 'moji');
  await page.getByRole('button', { name: 'Ponudba Menjava oken' }).click();
  await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
  const first = page.getByRole('list', { name: 'Izmere Rušenje estriha' }); await expect(first.getByRole('listitem')).toHaveCount(2);
  await expect(first.getByRole('listitem').nth(0)).toContainText(/\+\s?30\s?m²/); await expect(first.getByRole('listitem').nth(0)).toContainText(/6\s?×\s?5/);
  const second = page.getByRole('list', { name: 'Izmere Polaganje keramike' }); await expect(second.getByRole('listitem').nth(1)).toContainText(/−\s?1\s?m²/);
  await expect(page.getByText(/Skupaj izmer/).first()).toBeVisible();
  await expect(page.getByRole('main').getByText(/Material|delavc|Urna postavka|Število ur|Cena dela/i)).toHaveCount(0);
  for (const amount of [/990,00\s?€/, /217,80\s?€/, /1\.?207,80\s?€/]) await expect(page.getByRole('group', { name: 'Vsote ponudbe' })).toContainText(amount);
  await check(page, 'ponudba-stranka-izmere', info.project.name);
 });
});

test('celoten potek: projekt, ponudba, sprejem, termin, izvedba, račun in plačilo', async ({ page }, info) => {
 test.setTimeout(90_000);
 await mockFlow(page); await signIn(page);
 const back = () => page.getByRole('button', { name: 'Nazaj na projekte' }).click();
 // mojster: nov projekt
 await open(page, 'projekti');
 await page.getByLabel('E-pošta stranke').fill('janez@example.test'); await page.getByLabel('Naziv').fill('Prenova kuhinje');
 await page.getByLabel('Lokacija izvedbe').fill('Maribor, Glavni trg 1'); await page.getByLabel('Opis').fill('Beljenje po prenovi');
 await page.getByRole('button', { name: 'Ustvari projekt' }).click();
 await expect(page.getByRole('status').filter({ hasText: 'Projekt je ustvarjen.' })).toBeVisible();
 await expect(page.getByRole('heading', { level: 2, name: 'Pregled' })).toBeVisible();
 // mojster: osnutek ponudbe je brez postavk projekta onemogočen
 await rowAction(page, 'Prenova kuhinje', 'Ponudba');
 await page.getByRole('button', { name: 'Ustvari osnutek ponudbe' }).click();
 await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeDisabled();
 await back();
 // mojster: postavka projekta z vrsto dela in izmero 4 x 2 m2 (model v3)
 await rowAction(page, 'Prenova kuhinje', 'Postavke');
 await expect(page.getByText('Projekt še nima postavk.')).toBeVisible();
 await page.getByRole('button', { name: 'Nova postavka' }).click();
 const dialog = page.getByRole('dialog');
 for (const [label, value] of [['Naziv', 'Beljenje sten'], ['Opis', 'Dve plasti'], ['Cena na enoto', '125'], ['Popust (%)', '0'], ['Stopnja DDV (%)', '22']]) await dialog.getByLabel(label).fill(value);
 await dialog.getByLabel('Vrsta dela').selectOption({ label: 'Beljenje' }); await dialog.getByLabel('Enota').selectOption({ label: 'm²' });
 await dialog.getByRole('button', { name: 'Shrani postavko' }).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.getByRole('button', { name: 'Izmere Beljenje sten' }).click();
 await page.getByRole('dialog').getByLabel('Dolžina').fill('4'); await page.getByRole('dialog').getByLabel('Višina').fill('2');
 await expect(page.getByRole('dialog').getByRole('group', { name: 'Izračun izmere' })).toContainText(/8\s?m²/);
 await page.getByRole('dialog').getByRole('button', { name: 'Dodaj izmero' }).click();
 await page.keyboard.press('Escape');
 await expect(page.getByRole('group', { name: 'Vsote postavk' })).toContainText(/1\.?220,00\s?€/);
 // urejanje postavke: obrazec je izpolnjen, shranjevanje je PUT
 await page.getByRole('button', { name: 'Uredi Beljenje sten' }).click();
 await expect(page.getByRole('dialog').getByLabel('Naziv')).toHaveValue('Beljenje sten');
 const edited = page.waitForRequest(r => r.method() === 'PUT' && r.url().endsWith('/postavke/fi1'));
 await check(page, 'postavka-uredi', info.project.name);
 await page.getByRole('dialog').getByRole('button', { name: 'Shrani postavko' }).click(); await edited;
 await expect(page.getByRole('dialog')).toHaveCount(0);
 // ponudba: predogled živih postavk projekta, nato pošiljanje
 await page.getByRole('button', { name: 'Ponudba Prenova kuhinje' }).click(); // detail view keeps plain tab buttons
 await expect(page.getByRole('group', { name: 'Vsote ponudbe' })).toContainText(/1\.?220,00\s?€/);
 await expect(page.getByRole('button', { name: 'Ročni vnos' })).toHaveCount(0);
 await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeEnabled();
 // pošiljanje je nepovratno: najprej potrditev, preklic ne pošlje ničesar
 let sent = 0; page.on('request', r => { if (r.method() === 'POST' && r.url().endsWith('/ponudbe/fq1/poslji')) sent++; });
 await page.getByRole('button', { name: 'Pošlji stranki' }).click();
 await page.getByRole('button', { name: 'Prekliči' }).click(); expect(sent).toBe(0);
 await page.getByRole('button', { name: 'Pošlji stranki' }).click(); await expect(page.getByRole('button', { name: 'Potrdi pošiljanje' })).toBeVisible();
 await check(page, 'ponudba-posiljanje', info.project.name);
 await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
 await expect(page.getByRole('button', { name: 'Pripravi novo različico' })).toBeVisible();
 await check(page, 'potek-ponudba-poslana', info.project.name);
 // stranka: sprejem
 await open(page, 'moji');
 await page.getByRole('button', { name: 'Ponudba Prenova kuhinje' }).click();
 await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click(); await page.getByRole('button', { name: 'Potrdi sprejem' }).click();
 await expect(page.getByText('Sprejeta').first()).toBeVisible();
 // mojster: termin in izvedba
 await open(page, 'projekti');
 await expect(page.getByRole('heading', { level: 2, name: 'Termin' })).toBeVisible();
 // ponudba je v fazi termin samo za branje
 await rowAction(page, 'Prenova kuhinje', 'Ponudba');
 await expect(page.getByRole('heading', { name: /P-2026-002/ })).toBeVisible();
 for (const name of ['Dodaj iz cenika', 'Ročni vnos', 'Uredi Beljenje sten', 'Odstrani Beljenje sten', 'Pošlji stranki', 'Pripravi novo različico']) await expect(page.getByRole('button', { name })).toHaveCount(0);
 await back();
 await rowAction(page, 'Prenova kuhinje', 'Izvedba');
 await page.getByLabel('Začetek termina').fill('2026-11-10T08:00'); await page.getByLabel('Konec termina').fill('2026-11-11T16:00');
 await page.getByRole('button', { name: 'Potrdi termin' }).click();
 await page.getByRole('button', { name: 'Zaključi izvedbo' }).click();
 await expect(page.getByText(/Izvedba je zaključena/).first()).toBeVisible();
 await check(page, 'potek-izvedba-koncana', info.project.name);
 await back();
 // mojster: račun in plačilo
 await rowAction(page, 'Prenova kuhinje', 'Račun');
 await expect(page.getByRole('button', { name: 'Izdaj račun' })).toBeEnabled();
 await expect(page.getByLabel('Prejemnik', { exact: true })).toHaveValue('Janez Kranjc'); await expect(page.getByLabel('Naslov prejemnika')).toHaveValue('Maribor, Glavni trg 1');
 await check(page, 'racun-izdaja-obrazec', info.project.name);
 await page.getByLabel('Prejemnik', { exact: true }).fill('Janez Kranjc s.p.');
 const issued = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith('/racun/izdaj'));
 await page.getByRole('button', { name: 'Izdaj račun' }).click();
 await expect(page.getByRole('button', { name: 'Potrdi izdajo' })).toBeVisible();
 await check(page, 'racun-izdaja-potrditev', info.project.name);
 await page.getByRole('button', { name: 'Potrdi izdajo' }).click();
 expect((await issued).postDataJSON()).toMatchObject({ prejemnik_naziv: 'Janez Kranjc s.p.', prejemnik_naslov: 'Maribor, Glavni trg 1', zapade_dne: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) });
 await expect(page.getByRole('heading', { name: /R-2026-001/ })).toBeVisible();
 await page.getByRole('button', { name: 'Evidentiraj plačilo' }).click();
 await expect(page.getByText('Plačan').first()).toBeVisible();
 await expect(page.getByRole('group', { name: 'Vsote računa' })).toContainText(/1\.?220,00\s?€/);
 await check(page, 'potek-racun-placan', info.project.name);
 // stranka: izdan in plačan račun
 await open(page, 'moji');
 await page.getByRole('button', { name: 'Račun Prenova kuhinje' }).click();
 await expect(page.getByRole('heading', { name: /R-2026-001/ })).toBeVisible();
 await expect(page.getByText('Plačan').first()).toBeVisible();
 await check(page, 'potek-racun-stranka', info.project.name);
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

test.describe('Obvestila (toast)', () => {
 test.beforeEach(async ({ page }) => { await mockApi(page); await signIn(page); });
 test('po uspešnem shranjevanju postavke se pojavi toast v vidnem polju, ne prekriva glave in po 5 s izgine', async ({ page }) => {
  await open(page, 'cenik');
  await page.getByRole('button', { name: 'Nova postavka' }).click();
  const d = page.getByRole('dialog');
  await d.getByLabel('Naziv').fill('Barvanje fasade'); await d.getByLabel('Opis').fill('Dve plasti'); await d.getByLabel('Vrsta dela').selectOption('v1'); await d.getByLabel('Cena na enoto (€)').fill('18.50');
  await d.getByRole('button', { name: 'Shrani postavko' }).click();
  await page.mouse.move(0, 0);
  const toast = page.locator('.toast-region .toast');
  await expect(toast).toHaveCount(1); await expect(toast).toContainText('Postavka je shranjena.');
  await expect(page.locator('main p.notice')).toHaveCount(0);
  const started = Date.now();
  const box = (await toast.boundingBox())!, view = page.viewportSize()!;
  expect(box.x).toBeGreaterThanOrEqual(0); expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(view.width); expect(box.y + box.height).toBeLessThanOrEqual(view.height);
  for (const button of await page.locator('header button, .page-title button, main > section > header button').all()) {
   if (!(await button.isVisible())) continue;
   const b = (await button.boundingBox())!;
   const overlap = box.x < b.x + b.width && b.x < box.x + box.width && box.y < b.y + b.height && b.y < box.y + box.height;
   expect(overlap, `toast covers ${await button.innerText()}`).toBe(false);
  }
  expect(await layoutProblems(page)).toEqual([]);
  await expect(toast).toBeHidden({ timeout: 7000 });
  expect(Date.now() - started).toBeGreaterThanOrEqual(4000);
 });
});
