import { expect, test, type Page, type Route } from '@playwright/test';
import { companies, mockApi, quoteFull, signIn, type Mock } from './fixtures';

// G5 acceptance for US-04..US-07 in model v3: postavke in izmere na projektu, ponudba = predogled in pošiljanje, error paths, double submit, immutability, tenant switch, refocus, layout.
// Overrides are registered after mockApi, so they win; unmatched requests fall back to the shared mock.
// Row actions carry the line name ("Uredi Rušenje estriha"); the general "Uredi postavke" link to the project items is allowed on a draft.
const LINE_ACTION = /^(Uredi|Odstrani|Izmere) (Rušenje|Polaganje|Montaža)/;
const phone = (page: Page) => page.viewportSize()!.width < 800;
const A = companies[0].id;
const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, json: body });
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

async function goto(page: Page, screen: 'Projekti' | 'Moji projekti') {
 await page.goto('/');
 await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
 if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
 await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: screen, exact: true }).click();
 await expect(page.getByRole('heading', { level: 1, name: screen })).toBeVisible();
 await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}
async function boot(page: Page, options: Mock = {}) { await mockApi(page, options); await signIn(page); }
async function masterQuote(page: Page, options: Mock = {}) { await boot(page, options); await goto(page, 'Projekti'); await page.getByRole('button', { name: 'Ponudba Obnova kopalnice' }).click(); await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible(); }
async function customerQuote(page: Page, options: Mock = {}) { await boot(page, { customerQuote: 'poslana', ...options }); await goto(page, 'Moji projekti'); await page.getByRole('button', { name: 'Ponudba Menjava oken' }).click(); await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible(); }
async function progress(page: Page, options: Mock) { await boot(page, options); await goto(page, 'Projekti'); await page.getByRole('button', { name: 'Izvedba Nov estrih' }).click(); await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible(); }
async function itemsScreen(page: Page, options: Mock = {}) { await boot(page, options); await goto(page, 'Projekti'); await page.getByRole('button', { name: 'Postavke Obnova kopalnice' }).click(); await expect(page.getByRole('heading', { level: 1, name: 'Obnova kopalnice' })).toBeVisible(); }
async function fillItem(page: Page) {
 const dialog = page.getByRole('dialog');
 for (const [label, value] of [['Naziv', 'Beljenje'], ['Opis', 'Dve plasti'], ['Cena na enoto', '10'], ['Količina', '3'], ['Stopnja DDV (%)', '22']]) await dialog.getByLabel(label).fill(value);
 await dialog.getByLabel('Vrsta dela').selectOption({ label: 'Beljenje' }); await dialog.getByLabel('Enota').selectOption({ label: 'm²' });
 return dialog;
}
const postPostavke = (page: Page, handler: (route: Route) => unknown) => page.route('**/api/podjetja/*/projekti/*/postavke', route => route.request().method() === 'POST' ? handler(route) : route.fallback());
async function invoicePanel(page: Page, options: Mock) { await boot(page, options); await goto(page, 'Projekti'); await page.getByRole('button', { name: 'Račun Nov estrih' }).click(); await expect(page.getByRole('heading', { level: 1, name: 'Nov estrih' })).toBeVisible(); }
const noSideways = (page: Page) => expect(page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).resolves.toBe(true);
function counter(page: Page, pattern: RegExp, method = 'POST') { const hits: string[] = []; page.on('request', r => { if (r.method() === method && pattern.test(new URL(r.url()).pathname)) hits.push(r.url()); }); return hits; }

// ---------- error paths shown to the user in Slovenian ----------
const errors: [number, string, unknown][] = [
 [401, 'Seja je potekla. Prijavite se znova.', { detail: 'Seja je potekla. Prijavite se znova.' }],
 [403, 'Za to dejanje nimate pravice.', { detail: 'Za to dejanje nimate pravice.' }],
 [404, 'Zapis ni na voljo.', { detail: 'Zapis ni na voljo.' }],
 [409, 'Ponudba mora imeti vsaj eno postavko.', { detail: 'Ponudba mora imeti vsaj eno postavko.' }],
 [409, 'Vsaka postavka mora imeti pozitivno količino izmer.', { detail: 'Vsaka postavka mora imeti pozitivno količino izmer.' }],
 [422, 'Preverite vnesene podatke.', { detail: [{ loc: ['body', 'kolicina'], msg: 'x', type: 'value_error' }] }],
 [503, 'Podatkovna baza trenutno ni na voljo.', { detail: 'Podatkovna baza trenutno ni na voljo.' }],
];
test.describe('Napake strežnika pri pošiljanju ponudbe', () => {
 for (const [status, message, body] of errors) test(`HTTP ${status} »${message}« pokaže slovensko opozorilo, ponudba ostane osnutek, gumb je spet omogočen`, async ({ page }) => {
  await masterQuote(page);
  await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', route => json(route, body, status));
  await page.getByRole('button', { name: 'Pošlji stranki' }).click(); await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
  await expect(page.getByRole('alert')).toHaveText(message);
  await expect(page.getByText('Osnutek').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeEnabled();
  await noSideways(page);
 });
 test('shranjevanje postavke po sprejemu (409) pokaže sporočilo v predalu in ohrani vnos', async ({ page }) => {
  await itemsScreen(page);
  await postPostavke(page, route => json(route, { detail: 'V tej fazi projekta to dejanje ni dovoljeno.' }, 409));
  await page.getByRole('button', { name: 'Nova postavka' }).click();
  const dialog = await fillItem(page);
  await dialog.getByRole('button', { name: 'Shrani postavko' }).click();
  await expect(dialog.getByRole('alert')).toContainText('V tej fazi projekta to dejanje ni dovoljeno.');
  await expect(dialog.getByLabel('Naziv')).toHaveValue('Beljenje');
  await expect(dialog.getByRole('button', { name: 'Shrani postavko' })).toBeEnabled();
 });
 test('izmera, ki bi dala negativno količino (409), pokaže sporočilo v predalu in ohrani vnos', async ({ page }) => {
  await itemsScreen(page);
  await page.route('**/api/podjetja/*/projekti/*/postavke/i2/izmere', route => route.request().method() === 'POST' ? json(route, { detail: 'Izmere bi dale negativno količino.' }, 409) : route.fallback());
  await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
  const dialog = page.getByRole('dialog'); await dialog.getByLabel('Dolžina').fill('1'); await dialog.getByLabel('Višina').fill('1');
  await dialog.getByRole('button', { name: 'Dodaj izmero' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Izmere bi dale negativno količino.');
  await expect(dialog.getByLabel('Dolžina')).toHaveValue('1'); await expect(dialog.getByRole('button', { name: 'Dodaj izmero' })).toBeEnabled();
 });
 for (const status of [403, 404, 503]) test(`nalaganje postavk projekta vrne ${status}: opozorilo, ne prazno stanje 'Projekt še nima postavk.'`, async ({ page }) => {
  await boot(page); await goto(page, 'Projekti');
  await page.route('**/api/podjetja/*/projekti/*/postavke', route => json(route, { detail: status === 403 ? 'Za to dejanje nimate pravice.' : status === 404 ? 'Zapis ni na voljo.' : 'Podatkovna baza trenutno ni na voljo.' }, status));
  await page.getByRole('button', { name: 'Postavke Obnova kopalnice' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByText('Projekt še nima postavk.')).toHaveCount(0);
 });
 for (const status of [403, 404]) test(`nalaganje ponudb vrne ${status}: opozorilo, ne prazno stanje 'brez ponudbe'`, async ({ page }) => {
  await boot(page); await goto(page, 'Projekti');
  await page.route('**/api/podjetja/*/projekti/*/ponudbe', route => json(route, { detail: status === 403 ? 'Za to dejanje nimate pravice.' : 'Zapis ni na voljo.' }, status));
  await page.getByRole('button', { name: 'Ponudba Obnova kopalnice' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ustvari osnutek ponudbe' })).toHaveCount(0);
 });
 test('sprejem stranke: 409 (ponudba ni več odprta) pokaže sporočilo in ne spremeni stanja', async ({ page }) => {
  await customerQuote(page);
  await page.route('**/api/projekti/*/ponudbe/*/odlocitev', route => json(route, { detail: 'O tej ponudbi ni več mogoče odločati.' }, 409));
  await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click(); await page.getByRole('button', { name: 'Potrdi sprejem' }).click();
  await expect(page.getByRole('alert')).toHaveText('O tej ponudbi ni več mogoče odločati.');
  await expect(page.getByText('Sprejeta')).toHaveCount(0);
 });
 test('sprejem stranke: 403 (vloga odvzeta sredi seje) pokaže sporočilo', async ({ page }) => {
  await customerQuote(page);
  await page.route('**/api/projekti/*/ponudbe/*/odlocitev', route => json(route, { detail: 'Za to dejanje nimate pravice.' }, 403));
  await page.getByRole('button', { name: 'Zavrni ponudbo' }).click(); await page.getByRole('button', { name: 'Potrdi zavrnitev' }).click();
  await expect(page.getByRole('alert')).toHaveText('Za to dejanje nimate pravice.');
 });
 test('termin: 409 (v preteklosti) in 422 se pokažeta, obrazec ohrani vnos', async ({ page }) => {
  await progress(page, { progress: 'termin' });
  await page.route('**/api/podjetja/*/projekti/*/termin', route => json(route, { detail: 'Termin se ne sme začeti v preteklosti.' }, 409));
  await page.getByLabel('Začetek termina').fill('2026-11-10T08:00'); await page.getByLabel('Konec termina').fill('2026-11-11T08:00');
  await page.getByRole('button', { name: 'Potrdi termin' }).click();
  await expect(page.getByRole('alert')).toHaveText('Termin se ne sme začeti v preteklosti.');
  await expect(page.getByLabel('Začetek termina')).toHaveValue('2026-11-10T08:00');
 });
 for (const [status, detail] of [[409, 'Izvedbe ni mogoče zaključiti pred začetkom termina.'], [403, 'Za to dejanje nimate pravice.']] as const) test(`zaključek izvedbe ${status} pokaže sporočilo in izvedba ostane odprta`, async ({ page }) => {
  await progress(page, { progress: 'izvedba' });
  await page.route('**/api/podjetja/*/projekti/*/izvedba', route => json(route, { detail }, status));
  await page.getByRole('button', { name: 'Zaključi izvedbo' }).click();
  await expect(page.getByRole('alert')).toHaveText(detail);
  await expect(page.getByRole('button', { name: 'Zaključi izvedbo' })).toBeEnabled();
 });
 for (const [status, detail] of [[409, 'Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.'], [422, 'Preverite vnesene podatke.']] as const) test(`izdaja računa ${status} pokaže sporočilo, račun ostane osnutek`, async ({ page }) => {
  await invoicePanel(page, { invoice: 'osnutek-pripravljen' });
  await page.route('**/api/podjetja/*/projekti/*/racun/izdaj', route => json(route, status === 422 ? { detail: [{ loc: ['body'], msg: 'x', type: 'x' }] } : { detail }, status));
  await page.getByRole('button', { name: 'Izdaj račun' }).click(); await page.getByRole('button', { name: 'Potrdi izdajo' }).click();
  await expect(page.getByRole('alert')).toHaveText(detail);
  await expect(page.getByText('Osnutek računa')).toBeVisible();
 });
 test('plačilo 503 pokaže sporočilo in račun ostane neplačan', async ({ page }) => {
  await invoicePanel(page, { invoice: 'izdan' });
  await page.route('**/api/podjetja/*/projekti/*/racun/placilo', route => json(route, { detail: 'Podatkovna baza trenutno ni na voljo.' }, 503));
  await page.getByRole('button', { name: 'Evidentiraj plačilo' }).click();
  await expect(page.getByRole('alert')).toHaveText('Podatkovna baza trenutno ni na voljo.');
  await expect(page.getByText('Neplačan')).toBeVisible();
 });
 test('stranka: račun 403/503 pri nalaganju ni prikazan kot "Račun še ni izdan"', async ({ page }) => {
  await boot(page, { customerInvoice: 'izdan' }); await goto(page, 'Moji projekti');
  await page.route('**/api/projekti/*/racun', route => json(route, { detail: 'Podatkovna baza trenutno ni na voljo.' }, 503));
  await page.getByRole('button', { name: 'Račun Estrih v kleti' }).click();
  await expect(page.getByRole('alert')).toContainText('ni na voljo');
  await expect(page.getByText('Račun še ni izdan.')).toHaveCount(0);
 });
 test('odgovor brez JSON (npr. 502 prehoda) ne trdi, da so vneseni podatki napačni', async ({ page }) => {
  await masterQuote(page);
  await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', route => route.fulfill({ status: 502, contentType: 'text/html', body: '<html>Bad Gateway</html>' }));
  await page.getByRole('button', { name: 'Pošlji stranki' }).click(); await page.getByRole('button', { name: 'Potrdi pošiljanje' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('alert')).not.toHaveText('Preverite vnesene podatke.');
 });
});

// ---------- feedback must be visible where the user acted ----------
test('napaka sprejema je vidna in ni prekrita z glavo, ko stranka na dnu strani potrdi sprejem', async ({ page }) => {
 await customerQuote(page);
 await page.route('**/api/projekti/*/ponudbe/*/odlocitev', route => json(route, { detail: 'O tej ponudbi ni več mogoče odločati.' }, 409));
 await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
 await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
 await page.getByRole('button', { name: 'Potrdi sprejem' }).click();
 const alert = page.getByRole('alert');
 await expect(alert).toBeVisible();
 await page.waitForTimeout(300);
 const state = await alert.evaluate(el => { const r = el.getBoundingClientRect(), top = document.elementFromPoint(r.left + r.width / 2, Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1)); return { inView: r.top >= 0 && r.bottom <= innerHeight, reachable: !!top && (el === top || el.contains(top)) }; });
 expect(state).toEqual({ inView: true, reachable: true });
});

// ---------- double submit ----------
test.describe('Dvojna oddaja', () => {
 test('Pošlji stranki: dvojni klik pošlje en sam POST', async ({ page }) => {
  await masterQuote(page);
  const hits = counter(page, /ponudbe\/q1\/poslji$/);
  await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1/poslji', async route => { await wait(600); await json(route, { detail: 'Ponudba mora imeti vsaj eno postavko.' }, 409); });
  await page.getByRole('button', { name: 'Pošlji stranki' }).click();
  await page.getByRole('button', { name: 'Potrdi pošiljanje' }).dblclick();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Shrani postavko: Enter in klik med shranjevanjem pošljeta en sam POST, gumb je onemogočen', async ({ page }) => {
  await itemsScreen(page);
  const hits = counter(page, /\/postavke$/);
  await postPostavke(page, async route => { await wait(600); await json(route, { detail: 'V tej fazi projekta to dejanje ni dovoljeno.' }, 409); });
  await page.getByRole('button', { name: 'Nova postavka' }).click();
  const dialog = await fillItem(page);
  await dialog.getByLabel('Količina').press('Enter');
  await expect(dialog.locator('button[type="submit"]')).toBeDisabled();
  await dialog.getByLabel('Količina').press('Enter');
  await dialog.locator('button[type="submit"]').click({ force: true }).catch(() => undefined);
  await expect(dialog.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Dodaj izmero: dvojni klik pošlje en sam POST', async ({ page }) => {
  await itemsScreen(page);
  const hits = counter(page, /\/postavke\/i2\/izmere$/);
  await page.route('**/api/podjetja/*/projekti/*/postavke/i2/izmere', async route => { if (route.request().method() !== 'POST') return route.fallback(); await wait(600); await json(route, { detail: 'Izmere bi dale negativno količino.' }, 409); });
  await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
  const dialog = page.getByRole('dialog'); await dialog.getByLabel('Dolžina').fill('3'); await dialog.getByLabel('Višina').fill('2');
  await dialog.getByRole('button', { name: 'Dodaj izmero' }).dblclick();
  await expect(dialog.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Potrdi sprejem: dvojni klik pošlje eno odločitev', async ({ page }) => {
  await customerQuote(page);
  const hits = counter(page, /odlocitev$/);
  await page.route('**/api/projekti/*/ponudbe/*/odlocitev', async route => { await wait(600); await json(route, { detail: 'O tej ponudbi ni več mogoče odločati.' }, 409); });
  await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
  await page.getByRole('button', { name: 'Potrdi sprejem' }).dblclick();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Izdaj račun: dvojni klik in Enter pošljeta en sam POST', async ({ page }) => {
  await invoicePanel(page, { invoice: 'osnutek-pripravljen' });
  const hits = counter(page, /racun\/izdaj$/);
  await page.route('**/api/podjetja/*/projekti/*/racun/izdaj', async route => { await wait(600); await json(route, { detail: 'Rok plačila ne sme biti pred datumom izdaje.' }, 409); });
  await page.getByRole('button', { name: 'Izdaj račun' }).click();
  await page.getByRole('button', { name: 'Potrdi izdajo' }).dblclick();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Evidentiraj plačilo: dvojni klik pošlje en sam POST', async ({ page }) => {
  await invoicePanel(page, { invoice: 'izdan' });
  const hits = counter(page, /racun\/placilo$/);
  await page.route('**/api/podjetja/*/projekti/*/racun/placilo', async route => { await wait(600); await json(route, { detail: 'Podatkovna baza trenutno ni na voljo.' }, 503); });
  await page.getByRole('button', { name: 'Evidentiraj plačilo' }).dblclick();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
 test('Potrdi termin in Zaključi izvedbo: dvojni klik pošlje en sam zahtevek', async ({ page }) => {
  await progress(page, { progress: 'termin' });
  const hits = counter(page, /\/termin$/, 'PUT');
  await page.route('**/api/podjetja/*/projekti/*/termin', async route => { await wait(600); await json(route, { detail: 'Termin se ne sme začeti v preteklosti.' }, 409); });
  await page.getByLabel('Začetek termina').fill('2026-11-10T08:00'); await page.getByLabel('Konec termina').fill('2026-11-11T08:00');
  await page.getByRole('button', { name: 'Potrdi termin' }).dblclick();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(hits).toHaveLength(1);
 });
});

// ---------- immutability, customer isolation, distinct empty states ----------
test.describe('Nespremenljivost in vidnost', () => {
 test('poslana ponudba mojstra nima nobenega dejanja urejanja (dodaj, vnos, odstrani, pošlji)', async ({ page }) => {
  await masterQuote(page, { quote: 'poslana' });
  for (const name of [/^Dodaj iz cenika/, /^Ročni vnos/, /^Nova postavka/, /^Pošlji stranki/, /^Uredi /, /^Odstrani /]) await expect(page.getByRole('button', { name })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Pripravi novo različico' })).toBeVisible();
 });
 test('osnutek je predogled: vrstici sta vidni s skupno izmero, brez gumbov Uredi, Odstrani in Izmere', async ({ page }) => {
  await masterQuote(page, { quote: 'osnutek' });
  await expect(page.getByRole('row', { name: /Rušenje estriha/ })).toContainText(/45\s?m²/); await expect(page.getByRole('row', { name: /Polaganje keramike/ })).toContainText(/2\s?m²/);
  await expect(page.getByRole('button', { name: LINE_ACTION })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeEnabled();
 });
 test('zavrnjena ponudba: mojster vidi zavrnjeno različico in lahko pripravi novo', async ({ page }) => {
  await boot(page, { quote: 'poslana' });
  const rejected = { ...quoteFull('poslana'), stanje: 'zavrnjena', odgovorjeno_ob: '2026-11-07T10:00:00Z' }, { postavke, ddv_po_stopnjah, ...summary } = rejected;
  await page.route('**/api/podjetja/*/projekti/*/ponudbe', route => json(route, [summary]));
  await page.route('**/api/podjetja/*/projekti/*/ponudbe/q1', route => json(route, rejected));
  await goto(page, 'Projekti'); await page.getByRole('button', { name: 'Ponudba Obnova kopalnice' }).click();
  await expect(page.getByText('Zavrnjena').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pripravi novo različico' })).toBeVisible();
  for (const name of [/^Dodaj iz cenika/, /^Ročni vnos/, /^Pošlji stranki/, /^Uredi /, /^Odstrani /]) await expect(page.getByRole('button', { name })).toHaveCount(0);
 });
 test('stranka: pogled ponudbe in računa kliče samo stranske poti, nikoli poti mojstra, in ne pokaže materialov, osnutkov ali cene dela', async ({ page }) => {
  const urls: string[] = []; page.on('request', r => { const p = new URL(r.url()).pathname; if (p.startsWith('/api/')) urls.push(`${r.method()} ${p}`); });
  await customerQuote(page);
  await expect(page.getByRole('main')).not.toContainText(/Material:|Lepilo|Cement|nabavna|Urna postavka|Število ur|Število delavcev|Cena dela/);
  await expect(page.locator('.status-badge', { hasText: 'Osnutek' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Nazaj na projekte' }).click();
  expect(urls.filter(u => u.includes('/podjetja/') && /ponudbe|racun|termin|izvedba|postavke|vrste-dela/.test(u))).toEqual([]);
 });
 test('stranka: račun v osnutku se nikoli ne prikaže (404 -> Račun še ni izdan), brez gumbov za dejanja', async ({ page }) => {
  await boot(page); await goto(page, 'Moji projekti');
  await page.getByRole('button', { name: 'Račun Estrih v kleti' }).click();
  await expect(page.getByText('Račun še ni izdan.')).toBeVisible();
  await expect(page.getByRole('button', { name: /Izdaj|plačilo|Sprejmi|Zavrni/ })).toHaveCount(0);
 });
 test('prazno, ničelno in manjkajoče so ločeni: brez ponudbe / osnutek brez postavk projekta z 0,00 € / napaka', async ({ page }) => {
  await masterQuote(page, { quote: 'prazen' });
  await expect(page.getByRole('button', { name: 'Pošlji stranki' })).toBeDisabled();
  await expect(page.getByRole('group', { name: 'Vsote ponudbe' })).toContainText(/0,00\s?€/);
  await expect(page.getByText('Projekt še nima ponudbe.')).toHaveCount(0);
 });
 test('postavka brez izmer je označena v seznamu postavk, izmera m² ne ponuja širine', async ({ page }) => {
  await itemsScreen(page);
  await expect(page.getByRole('row', { name: /Montaža vrat/ })).toContainText('Brez izmer'); await expect(page.getByRole('row', { name: /Polaganje keramike/ })).not.toContainText('Brez izmer');
  await page.getByRole('button', { name: 'Izmere Polaganje keramike' }).click();
  await expect(page.getByRole('dialog').getByLabel('Širina')).toHaveCount(0);
 });
 test('plačilo: ni polja za znesek (samo celotno plačilo), plačan račun nima dejanj', async ({ page }) => {
  await invoicePanel(page, { invoice: 'izdan' });
  await expect(page.getByRole('main').locator('input[type=number], input[name*=znesek]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Evidentiraj plačilo' })).toBeVisible();
 });
 test('račun v osnutku pred zaključeno izvedbo: izdaja onemogočena, brez obrazca za rok', async ({ page }) => {
  await invoicePanel(page, { invoice: 'osnutek' });
  await expect(page.getByRole('button', { name: 'Izdaj račun' })).toBeDisabled();
  await expect(page.getByLabel('Rok plačila')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Osnutek računa' })).toBeVisible();
 });
 test('termin pred sprejemom: obrazca za termin ni, izvedba ni zaključena', async ({ page }) => {
  await boot(page); await goto(page, 'Projekti');
  await expect(page.getByRole('button', { name: 'Izvedba Obnova kopalnice' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Račun Obnova kopalnice' })).toHaveCount(0);
 });
 test('vnos termina ne označi dela kot opravljenega: po potrditvi je gumb Zaključi izvedbo še vedno na voljo', async ({ page }) => {
  await progress(page, { progress: 'izvedba' });
  await expect(page.getByText(/Izvedba je zaključena/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Zaključi izvedbo' })).toBeVisible();
 });
});

// ---------- active company switch, refocus ----------
test.describe('Podjetje in fokus', () => {
 test('preklop podjetja sredi dela ne pokaže podatkov prejšnjega podjetja', async ({ page }) => {
  await boot(page);
  const B = companies[1].id;
  await page.route('**/api/me', route => json(route, { id: 'u0000000-0000-4000-8000-000000000001', e_posta: 'ana@mojster.example.test', ime: 'Ana', priimek: 'Novak', vloge: [{ id: 'r2', podjetje_id: A, vloga: 'mojster', naziv: companies[0].naziv }, { id: 'r9', podjetje_id: B, vloga: 'mojster', naziv: companies[1].naziv }, { id: 'r3', podjetje_id: null, vloga: 'stranka', naziv: null }] }));
  await page.route(`**/api/podjetja/${B}/projekti`, async route => { await wait(400); await json(route, []); });
  await page.route(`**/api/podjetja/${B}/cenik`, route => json(route, []));
  await goto(page, 'Projekti');
  await page.getByRole('button', { name: 'Ponudba Obnova kopalnice' }).click();
  await expect(page.getByRole('heading', { name: /P-2026-001/ })).toBeVisible();
  if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
  await page.getByLabel('Aktivno podjetje').selectOption(B);
  await expect(page.getByText(/P-2026-001|Obnova kopalnice|Rušenje estriha/)).toHaveCount(0);
  if (phone(page)) await page.getByRole('button', { name: 'Meni' }).click();
  await page.getByRole('navigation', { name: 'Glavna navigacija' }).getByRole('button', { name: 'Projekti', exact: true }).click();
  await expect(page.getByText('Še ni projektov')).toBeVisible();
  await expect(page.getByText(/P-2026-001|Obnova kopalnice/)).toHaveCount(0);
 });
 test('ponovni fokus brskalnika z odprtim obrazcem postavke ohrani vnos in ne sproži ponovnega nalaganja', async ({ page }) => {
  await itemsScreen(page);
  await page.getByRole('button', { name: 'Nova postavka' }).click();
  const dialog = page.getByRole('dialog'); await dialog.getByLabel('Naziv').fill('Vnos v teku'); await dialog.getByLabel('Količina').fill('7');
  const gets = counter(page, /\/postavke|\/cenik|\/vrste-dela/, 'GET');
  await page.evaluate(() => { window.dispatchEvent(new Event('blur')); document.dispatchEvent(new Event('visibilitychange')); window.dispatchEvent(new Event('focus')); document.dispatchEvent(new Event('visibilitychange')); });
  await page.waitForTimeout(400);
  await expect(dialog.getByLabel('Naziv')).toHaveValue('Vnos v teku'); await expect(dialog.getByLabel('Količina')).toHaveValue('7');
  expect(gets).toEqual([]);
 });
 test('ponovni fokus z obrazcem termina ohrani vnos', async ({ page }) => {
  await progress(page, { progress: 'termin' });
  await page.getByLabel('Začetek termina').fill('2026-11-10T08:00');
  await page.evaluate(() => { window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus')); document.dispatchEvent(new Event('visibilitychange')); });
  await page.waitForTimeout(300);
  await expect(page.getByLabel('Začetek termina')).toHaveValue('2026-11-10T08:00');
 });
 test('ponovni fokus s potrditvijo sprejema ohrani potrditev', async ({ page }) => {
  await customerQuote(page);
  await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click();
  await page.evaluate(() => { window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus')); });
  await expect(page.getByRole('button', { name: 'Potrdi sprejem' })).toBeVisible();
 });
});

// ---------- layout at both widths ----------
test.describe('Postavitev', () => {
 test('seznam postavk projekta in predogled ponudbe ne prelivata zaslona', async ({ page }) => {
  await itemsScreen(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'postavke projekta scroll sideways').toBe(true);
  await page.screenshot({ path: `test-results/screens/acceptance-postavke-${phone(page) ? 'phone' : 'desktop'}.png`, fullPage: true });
 });
 test('stranski paneli postavk (cenik, nova postavka, izmere) ne prelivajo zaslona', async ({ page }) => {
  await itemsScreen(page);
  for (const [button, shot] of [['Dodaj iz cenika', 'cenik'], ['Nova postavka', 'postavka'], ['Izmere Polaganje keramike', 'izmere']]) {
   await page.getByRole('button', { name: button }).click();
   await page.evaluate(async () => { await Promise.allSettled(document.getAnimations().map(a => a.finished)); });
   const box = await page.getByRole('dialog').boundingBox();
   expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
   expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `page scrolls sideways with the "${button}" panel open`).toBe(true);
   await page.screenshot({ path: `test-results/screens/acceptance-${shot}-panel-${phone(page) ? 'phone' : 'desktop'}.png`, fullPage: true });
   await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
  }
 });
 test('napaka in potrditev na ponudbi stranke ne prelivata zaslona', async ({ page }) => {
  await customerQuote(page);
  await page.route('**/api/projekti/*/ponudbe/*/odlocitev', route => json(route, { detail: 'O tej ponudbi ni več mogoče odločati.' }, 409));
  await page.getByRole('button', { name: 'Sprejmi ponudbo' }).click(); await page.getByRole('button', { name: 'Potrdi sprejem' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await noSideways(page);
  for (const name of ['Potrdi sprejem', 'Prekliči']) { const box = await page.getByRole('button', { name }).boundingBox(); expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1); expect(box!.height).toBeGreaterThanOrEqual(phone(page) ? 39.5 : 27.5); }
  await page.screenshot({ path: `test-results/screens/acceptance-stranka-napaka-${phone(page) ? 'phone' : 'desktop'}.png`, fullPage: true });
 });
 test('račun in potek na telefonu in namizju ne prelivata zaslona', async ({ page }) => {
  await invoicePanel(page, { invoice: 'izdan' });
  await noSideways(page);
  await page.screenshot({ path: `test-results/screens/acceptance-racun-${phone(page) ? 'phone' : 'desktop'}.png`, fullPage: true });
 });
});
