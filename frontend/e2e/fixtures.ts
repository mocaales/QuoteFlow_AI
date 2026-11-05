import type { Page } from '@playwright/test';
// Fictional company examples for V2 browser checks.
const SUPABASE='https://qf-demo.supabase.co';
const A='a0000000-0000-4000-8000-000000000001', B='b0000000-0000-4000-8000-000000000002';
const USER={id:'u0000000-0000-4000-8000-000000000001',email:'ana@mojster.example.test'};
export const companies=[
 {id:A,lastnik_id:USER.id,naziv:'Mojster Novak d.o.o.',maticna_stevilka:'1234567',davcna_stevilka:'SI12345678',naslov:'Cesta 1, Maribor',aktivno:true},
 {id:B,lastnik_id:'u2',naziv:'Gradnje Kos d.o.o.',maticna_stevilka:'7654321',davcna_stevilka:'SI87654321',naslov:'Ulica 2, Celje',aktivno:true},
];
const profile={id:USER.id,e_posta:USER.email,ime:'Ana',priimek:'Novak',vloge:[
 {id:'r1',podjetje_id:null,vloga:'admin',naziv:null},
 {id:'r2',podjetje_id:A,vloga:'mojster',naziv:companies[0].naziv},
 {id:'r3',podjetje_id:null,vloga:'stranka',naziv:null},
]};
export const catalog=[
 {id:'i1',podjetje_id:A,naziv:'Rušenje estriha',opis:'Odstranitev obstoječega estriha in odvoz',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'12.4500',stopnja_ddv:'.22',aktivna:true},
 {id:'i2',podjetje_id:A,naziv:'Polaganje keramike',opis:'Priprava podlage in polaganje',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'35.0000',stopnja_ddv:'.22',aktivna:true},
 {id:'i3',podjetje_id:A,naziv:'Zaključno čiščenje',opis:'Čiščenje prostora',vrsta_dela:'Čiščenje',enota:'ura',cena_na_enoto:'20.0000',stopnja_ddv:'.095',aktivna:false},
];
const kinds=[{id:'k1',podjetje_id:A,naziv:'Lepila'},{id:'k2',podjetje_id:A,naziv:'Gradbeni material'}];
const materials=[
 {id:'m1',vrsta_materiala_id:'k1',sifra:'LEP-1',naziv:'Lepilo za ploščice',enota:'kg',cena_na_enoto:'2.5000',aktiven:true},
 {id:'m2',vrsta_materiala_id:'k2',sifra:'CEM-1',naziv:'Cement',enota:'kg',cena_na_enoto:'0.2500',aktiven:true},
];
const stocks:Record<string,unknown[]>={m1:[{material_id:'m1',lokacija:'Maribor',kolicina:'40'},{material_id:'m1',lokacija:'Celje',kolicina:'0'}],m2:[]};
const users=[{id:USER.id,e_posta:USER.email,ime:'Ana',priimek:'Novak'},{id:'u2',e_posta:'marko@example.test',ime:'Marko',priimek:'Kos'}];
const roles=[
 {id:'r1',uporabnik_id:USER.id,e_posta:USER.email,podjetje_id:null,naziv:null,vloga:'admin',aktivna:true},
 {id:'r2',uporabnik_id:USER.id,e_posta:USER.email,podjetje_id:A,naziv:companies[0].naziv,vloga:'mojster',aktivna:true},
 {id:'r3',uporabnik_id:'u2',e_posta:'marko@example.test',podjetje_id:B,naziv:companies[1].naziv,vloga:'delavec',aktivna:true},
];

export const ownRequests=[
 {id:'p1',uporabnik_id:USER.id,naziv_podjetja:'Parketarstvo Ana s.p.',maticna_stevilka:'5551234000',davcna_stevilka:null,naslov_podjetja:'Glavna cesta 5, Ptuj',stanje:'zavrnjena',podjetje_id:null,oddano_ob:'2026-10-20T09:30:00Z',odloceno_ob:'2026-10-21T08:00:00Z'},
];
export const masterRequests=[
 {id:'p2',uporabnik_id:'u2',naziv_podjetja:'Elektro Kos d.o.o.',maticna_stevilka:'6667890000',davcna_stevilka:'SI66678900',naslov_podjetja:'Ulica 2, Celje',stanje:'oddana',podjetje_id:null,oddano_ob:'2026-11-03T10:15:00Z',odloceno_ob:null,e_posta:'marko@example.test',ime:'Marko',priimek:'Kos'},
 {id:'p3',uporabnik_id:'u3',naziv_podjetja:'Zidarstvo Horvat s.p.',maticna_stevilka:'7778901000',davcna_stevilka:null,naslov_podjetja:'Trg 3, Kranj',stanje:'odobrena',podjetje_id:B,oddano_ob:'2026-10-25T12:00:00Z',odloceno_ob:'2026-10-26T09:00:00Z',e_posta:'jure@example.test',ime:'Jure',priimek:'Horvat'},
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
  if (path.endsWith('/vrste-materiala')) return json(kinds);
  if (path.endsWith('/materiali')) return json(materials);
  if (path.endsWith('/zaloga')) return json(stocks[path.split('/').at(-2)!] ?? []);
  if (path === '/prosnje') return json(route.request().method() === 'POST' ? ownRequests[0] : ownRequests, route.request().method() === 'POST' ? 201 : 200);
  if (path === '/admin/prosnje') return json(masterRequests);
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
