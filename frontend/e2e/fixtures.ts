import type { Page } from '@playwright/test';
// Sample data for the browser checks only: a fictional bearings supplier and its buyer.
const SUPABASE = 'https://qf-demo.supabase.co';
const A = 'a0000000-0000-4000-8000-000000000001', B = 'b0000000-0000-4000-8000-000000000002', C = 'c0000000-0000-4000-8000-000000000003';
const USER = { id: 'u0000000-0000-4000-8000-000000000001', email: 'nina.zupan@lezajna-tehnika.si' };

export const companies = [
 { id: A, naziv: 'Ležajna tehnika d.o.o.', stanje: 'aktivno' },
 { id: B, naziv: 'Strojna oprema Kranj d.o.o.', stanje: 'aktivno' },
 { id: C, naziv: 'Hidravlika Novak d.o.o.', stanje: 'neaktivno' },
];
const profile = { id: USER.id, e_posta: USER.email, vloge: [
 { id: 'r1', podjetje_id: null, vloga: 'administrator', naziv: null },
 { id: 'r2', podjetje_id: A, vloga: 'ponudnik', naziv: companies[0].naziv },
] };
const item = (id: string, vrsta: string, opis: string, enota: string, cena: string, strosek: string, rok: number | null, potrjeno: boolean, zaloga: string | null, aktivna = true) => ({
 id, podjetje_id: A, vrsta, opis, enota, cena_na_enoto: cena, strosek_na_enoto: strosek, dobavni_rok_dni: rok, aktivna,
 potrjeno_ob: potrjeno ? '2026-10-27T08:15:00Z' : null, razpolozljiva_kolicina: zaloga, zaloga_potrjeno_ob: zaloga === null ? null : '2026-10-29T13:40:00Z',
});
export const catalog = [
 item('i1', 'blago', 'Kroglični ležaj SKF 6205-2RS', 'kos', '12.4500', '8.1000', 5, true, '340'),
 item('i2', 'blago', 'Kroglični ležaj SKF 6206-2RS', 'kos', '15.9000', '10.4000', 5, true, '0'),
 item('i3', 'blago', 'Valjčni ležaj NU 2208 ECP', 'kos', '48.2000', '31.5000', 10, false, null),
 item('i4', 'blago', 'Mazivo za ležaje LGMT 2', 'kg', '18.6000', '11.2000', 3, true, '42.5'),
 item('i5', 'storitev', 'Montaža ležajev na lokaciji kupca', 'ura', '55.0000', '32.0000', null, true, null),
 item('i6', 'blago', 'Radialno tesnilo CR 25x52x7', 'kos', '2.3500', '1.1000', 7, false, null, false),
];
export const rules = [
 { id: 'p3', podjetje_id: A, najmanjsa_marza: '0.200000', najvecji_popust: '0.080000', najdaljsi_rok_dni: 21, velja_od: '2027-01-01T00:00:00+01:00', velja_do: null },
 { id: 'p2', podjetje_id: A, najmanjsa_marza: '0.180000', najvecji_popust: '0.100000', najdaljsi_rok_dni: 21, velja_od: '2026-09-01T00:00:00+02:00', velja_do: '2027-01-01T00:00:00+01:00' },
 { id: 'p1', podjetje_id: A, najmanjsa_marza: '0.150000', najvecji_popust: '0.120000', najdaljsi_rok_dni: 30, velja_od: '2026-01-01T00:00:00+01:00', velja_do: '2026-09-01T00:00:00+02:00' },
];
const users = [USER, { id: 'u2', email: 'marko.kos@strojna-kranj.si' }, { id: 'u3', email: 'tina.novak@hidravlika-novak.si' }].map(u => ({ id: u.id, e_posta: u.email }));
const roles = [
 { id: 'r1', uporabnik_id: USER.id, e_posta: USER.email, podjetje_id: null, naziv: null, vloga: 'administrator', aktivna: true },
 { id: 'r2', uporabnik_id: USER.id, e_posta: USER.email, podjetje_id: A, naziv: companies[0].naziv, vloga: 'ponudnik', aktivna: true },
 { id: 'r3', uporabnik_id: 'u2', e_posta: 'marko.kos@strojna-kranj.si', podjetje_id: B, naziv: companies[1].naziv, vloga: 'nabavnik', aktivna: true },
 { id: 'r4', uporabnik_id: 'u3', e_posta: 'tina.novak@hidravlika-novak.si', podjetje_id: C, naziv: companies[2].naziv, vloga: 'ponudnik', aktivna: false },
];

export type Mock = { catalogStatus?: number };
export async function mockApi(page: Page, options: Mock = {}) {
 await page.route(`${SUPABASE}/**`, route => route.fulfill({ status: 200, json: {} }));
 await page.route('**/api/**', route => {
  const path = new URL(route.request().url()).pathname.replace(/^\/api/, '');
  const json = (body: unknown, status = 200) => route.fulfill({ status, json: body });
  if (path === '/config') return json({ supabase_url: SUPABASE, supabase_publishable_key: 'sb_publishable_demo' });
  if (path === '/health') return json({ status: 'ok' });
  if (path === '/me') return json(profile);
  if (path === '/podjetja') return json(companies);
  if (path.endsWith('/cenik')) return options.catalogStatus ? json({ detail: 'Podatkovna baza trenutno ni na voljo.' }, options.catalogStatus) : json(catalog);
  if (path.endsWith('/pravila')) return json(rules);
  if (path === '/admin/uporabniki') return json(users);
  if (path === '/admin/vloge') return json(roles);
  return json({ detail: 'Ni najdeno.' }, 404);
 });
}

// A signed-in browser session, stored where supabase-js looks for it (sessionStorage, sb-<ref>-auth-token).
export async function signIn(page: Page) {
 const b64 = (value: object) => Buffer.from(JSON.stringify(value)).toString('base64url');
 const exp = Math.floor(Date.now() / 1000) + 86400;
 const session = { access_token: `${b64({ alg: 'HS256' })}.${b64({ sub: USER.id, role: 'authenticated', session_id: 's1', exp })}.sig`,
  token_type: 'bearer', expires_in: 86400, expires_at: exp, refresh_token: 'demo-refresh',
  user: { id: USER.id, email: USER.email, aud: 'authenticated', role: 'authenticated', app_metadata: {}, user_metadata: {}, created_at: '2026-10-01T00:00:00Z' } };
 await page.addInitScript(value => sessionStorage.setItem('sb-qf-demo-auth-token', value), JSON.stringify(session));
}
