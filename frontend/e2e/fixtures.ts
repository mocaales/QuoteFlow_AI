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
 {id:'i1',podjetje_id:A,naziv:'Rušenje estriha',opis:'Odstranitev obstoječega estriha in odvoz',vrsta_dela_id:'v2',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'12.4500',stopnja_ddv:'.22',aktivna:true},
 {id:'i2',podjetje_id:A,naziv:'Polaganje keramike',opis:'Priprava podlage in polaganje',vrsta_dela_id:'v1',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'35.0000',stopnja_ddv:'.22',aktivna:true},
 {id:'i3',podjetje_id:A,naziv:'Zaključno čiščenje',opis:'Čiščenje prostora',vrsta_dela_id:'v3',vrsta_dela:'Staro delo',enota:'kos',cena_na_enoto:'20.0000',stopnja_ddv:'.095',aktivna:false},
];
const kinds=[{id:'k1',podjetje_id:A,naziv:'Lepila'},{id:'k2',podjetje_id:A,naziv:'Gradbeni material'}];
const materials=[
 {id:'m1',vrsta_materiala_id:'k1',sifra:'LEP-1',naziv:'Lepilo za ploščice',enota:'kg',cena_na_enoto:'2.5000',aktiven:true},
 {id:'m2',vrsta_materiala_id:'k2',sifra:'CEM-1',naziv:'Cement',enota:'kg',cena_na_enoto:'0.2500',aktiven:true},
];
const stocks:Record<string,unknown[]>={m1:[{material_id:'m1',lokacija:'Maribor',kolicina:'40'},{material_id:'m1',lokacija:'Celje',kolicina:'0'}],m2:[]};
const users=[
 {id:USER.id,e_posta:USER.email,ime:'Ana',priimek:'Novak',potrjen:true},{id:'u2',e_posta:'marko@example.test',ime:'Marko',priimek:'Kos',potrjen:true},
 {id:'u3',e_posta:'tina.zupan@example.test',ime:'Tina',priimek:'Zupan',potrjen:true},{id:'u4',e_posta:'peter.horvat@example.test',ime:'Peter',priimek:'Horvat',potrjen:true},
 {id:'u5',e_posta:'nina.krajnc@example.test',ime:'Nina',priimek:'Krajnc',potrjen:true},{id:'u6',e_posta:'neznan@example.test',ime:'Neznan',priimek:'Uporabnik',potrjen:false},
];
const person=(id:string)=>{const u=users.find(x=>x.id===id)!;return {uporabnik_id:u.id,e_posta:u.e_posta,ime:u.ime,priimek:u.priimek};};
const role=(id:string,u:string,podjetje:string|null,vloga:string,aktivna=true,je_lastnik=false)=>({id,...person(u),podjetje_id:podjetje,naziv:podjetje?companies.find(c=>c.id===podjetje)!.naziv:null,vloga,aktivna,je_lastnik,dodeljeno_ob:'2026-11-03T09:00:00Z'});
// Podjetje A: lastnik Ana (mojster), delavca Marko in Tina, odvzet Peter; podjetje B: lastnik Marko (mojster), delavka Tina odvzeta.
export const roles=[
 role('r1',USER.id,null,'admin'),role('r2',USER.id,A,'mojster',true,true),role('r4','u2',null,'stranka'),role('r3','u2',B,'mojster',true,true),
 role('r5','u2',A,'delavec'),role('r6','u3',A,'delavec'),role('r7','u4',A,'delavec',false),role('r8','u3',B,'delavec',false),role('r9','u3',null,'stranka'),
];
export const workers=[
 {id:'w1',uporabnik_id:'u2',e_posta:'marko@example.test',ime:'Marko',priimek:'Kos',aktivna:true,dodeljeno_ob:'2026-11-03T09:00:00Z'},
 {id:'w2',uporabnik_id:USER.id,e_posta:USER.email,ime:'Ana',priimek:'Novak',aktivna:true,dodeljeno_ob:'2026-11-01T09:00:00Z'},
 {id:'w3',uporabnik_id:'u3',e_posta:'tina.zupan@example.test',ime:'Tina',priimek:'Zupan',aktivna:true,dodeljeno_ob:'2026-11-04T09:00:00Z'},
 {id:'w4',uporabnik_id:'u4',e_posta:'peter.horvat@example.test',ime:'Peter',priimek:'Horvat',aktivna:false,dodeljeno_ob:'2026-11-02T09:00:00Z'},
];
// Vrsta dela nosi delo (cena dela = urna postavka x ure x delavci) in materiale na enoto mere; postavka cenika kaže nanjo.
export const composition=[{material_id:'m1',sifra:'LEP-1',naziv:'Lepilo za ploščice',enota:'kg',aktiven:true,kolicina_na_enoto:'4.5000',cena_na_enoto:'2.5000'},{material_id:'m2',sifra:'CEM-1',naziv:'Cement',enota:'kg',aktiven:true,kolicina_na_enoto:'1.2000',cena_na_enoto:'0.2500'}];
export const trades=[
 {id:'v1',naziv:'Keramika',opis:'Polaganje ploščic',urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,aktivna:true,cena_dela:'400.00',materiali:composition},
 {id:'v2',naziv:'Rušenje',opis:'Rušenje brez posebnega dela',urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,aktivna:true,cena_dela:'0.00',materiali:[]},
 {id:'v4',naziv:'Beljenje',opis:'Beljenje sten',urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,aktivna:true,cena_dela:'0.00',materiali:[]},
 {id:'v3',naziv:'Staro delo',opis:'',urna_postavka:'20.0000',stevilo_ur:'1.0000',stevilo_delavcev:1,aktivna:false,cena_dela:'20.00',materiali:[]},
];
// Postavke projekta (model v3, formula A): 45 m2 x 20 EUR, popust 10 % = 810,00; 20 m2 x 10 EUR + 25 EUR x 8 h x 2 delavca = 600, popust 10 % = 540,00.
// Vsota neto 1.350,00, DDV 22 % 297,00, skupaj 1.647,00. Montaža vrat nima izmer in je zato označena.
const dimension=(id:string,zaporedje:number,odstej:boolean,dolzina:string,visina:string,vrednost:string)=>({id,zaporedje,odstej,kosi:'1.0000',dolzina,visina,sirina:null,vrednost});
const itemBase={opis:'Opis',kolicina:'1.0000',popust:'0.000000',stopnja_ddv:'0.220000',urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,izmera_skupaj:'0.0000',cena_dela:'0.00',neto:'0.00',ddv:'0.00',koncna_cena:'0.00',izmere:[] as unknown[]};
export const projectItems={postavke:[
 {...itemBase,id:'i1',zaporedje:1,naziv:'Rušenje estriha',opis:'Odstranitev obstoječega estriha',vrsta_dela_id:'v2',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'20.0000',popust:'0.100000',izmera_skupaj:'45.0000',neto:'810.00',ddv:'178.20',koncna_cena:'988.20',
  izmere:[dimension('z1',1,false,'6.0000','5.0000','30.0000'),dimension('z2',2,false,'5.0000','3.0000','15.0000')]},
 {...itemBase,id:'i2',zaporedje:2,naziv:'Polaganje keramike',opis:'Priprava podlage in polaganje',vrsta_dela_id:'v1',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'10.0000',popust:'0.100000',urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,izmera_skupaj:'20.0000',cena_dela:'400.00',neto:'540.00',ddv:'118.80',koncna_cena:'658.80',
  izmere:[dimension('z3',1,false,'5.0000','4.0000','20.0000'),dimension('z4',2,false,'2.0000','1.0000','2.0000'),dimension('z5',3,true,'1.0000','2.0000','2.0000')]},
 {...itemBase,id:'i3',zaporedje:3,naziv:'Montaža vrat',opis:'Notranja vrata',vrsta_dela_id:'v2',vrsta_dela:'Rušenje',enota:'kos',cena_na_enoto:'80.0000'},
],neto:'1350.00',ddv:'297.00',skupaj:'1647.00'};


export const ownRequests=[
 {id:'p1',uporabnik_id:USER.id,naziv_podjetja:'Parketarstvo Ana s.p.',maticna_stevilka:'5551234000',davcna_stevilka:null,naslov_podjetja:'Glavna cesta 5, Ptuj',stanje:'zavrnjena',podjetje_id:null,oddano_ob:'2026-10-20T09:30:00Z',odloceno_ob:'2026-10-21T08:00:00Z'},
];
export const masterRequests=[
 {id:'p2',uporabnik_id:'u2',naziv_podjetja:'Elektro Kos d.o.o.',maticna_stevilka:'6667890000',davcna_stevilka:'SI66678900',naslov_podjetja:'Ulica 2, Celje',stanje:'oddana',podjetje_id:null,oddano_ob:'2026-11-03T10:15:00Z',odloceno_ob:null,e_posta:'marko@example.test',ime:'Marko',priimek:'Kos'},
 {id:'p3',uporabnik_id:'u3',naziv_podjetja:'Zidarstvo Horvat s.p.',maticna_stevilka:'7778901000',davcna_stevilka:null,naslov_podjetja:'Trg 3, Kranj',stanje:'odobrena',podjetje_id:B,oddano_ob:'2026-10-25T12:00:00Z',odloceno_ob:'2026-10-26T09:00:00Z',e_posta:'jure@example.test',ime:'Jure',priimek:'Horvat'},
];

export const projects=[
 {id:'pr1',naziv:'Obnova kopalnice',opis:'Rušenje estriha in nova keramika',lokacija_izvedbe:'Maribor, Glavni trg 1',faza:'pregled',stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'janez@example.test',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null},
 {id:'pr2',naziv:'Menjava oken',opis:'Šest oken',lokacija_izvedbe:'Celje, Cesta 5',faza:'ponudba',stranka_ime:'Maja',stranka_priimek:'Zupan',stranka_e_posta:'maja@example.test',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null},
 {id:'pr3',naziv:'Nov estrih',opis:'Estrih 40 m2',lokacija_izvedbe:'Ptuj, Slovenska 3',faza:'izvedba',stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'janez@example.test',termin_od:'2026-11-10T08:00:00Z',termin_do:'2026-11-12T16:00:00Z',izvedba_koncana_ob:null,zakljuceno_ob:null},
];
export const ownProjects=[
 {id:'pr1',naziv:'Obnova kopalnice',opis:'Rušenje estriha in nova keramika',lokacija_izvedbe:'Maribor, Glavni trg 1',faza:'pregled',podjetje_naziv:'Mojster Novak d.o.o.',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null},
 {id:'pr4',naziv:'Beljenje stanovanja',opis:'80 m2',lokacija_izvedbe:'Kranj, Trg 3',faza:'ogled',podjetje_naziv:'Gradnje Kos d.o.o.',termin_od:'2026-11-08T09:00:00Z',termin_do:'2026-11-08T10:00:00Z',izvedba_koncana_ob:null,zakljuceno_ob:null},
 {id:'pr6',naziv:'Estrih v kleti',opis:'Estrih 30 m2',lokacija_izvedbe:'Ptuj, Slovenska 3',faza:'obracun',podjetje_naziv:'Mojster Novak d.o.o.',termin_od:'2026-11-10T08:00:00Z',termin_do:'2026-11-12T16:00:00Z',izvedba_koncana_ob:'2026-11-12T16:30:00Z',zakljuceno_ob:null},
 {id:'pr5',naziv:'Menjava oken',opis:'Šest oken',lokacija_izvedbe:'Celje, Cesta 5',faza:'ponudba',podjetje_naziv:'Mojster Novak d.o.o.',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null},
];

const quoteLines=[
 {id:'l1',postavka_cenika_id:null,zaporedje:1,naziv:'Rušenje estriha',opis:'Odstranitev obstoječega estriha',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'20.0000',kolicina:'1.0000',izmera_skupaj:'45.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'810.00',ddv:'178.20',koncna_cena:'988.20',materiali:[]},
 {id:'l2',postavka_cenika_id:'i2',zaporedje:2,naziv:'Polaganje keramike',opis:'Priprava podlage in polaganje',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'100.0000',kolicina:'1.0000',izmera_skupaj:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60',
  materiali:[{material_id:'m1',naziv:'Lepilo za ploščice',enota:'kg',kolicina_na_enoto:'4.5000',cena_na_enoto:'2.5000',kolicina_skupaj:'9.0000'}]},
];
const quoteBase={id:'q1',stevilka:'P-2026-001',razlicica:1,stanje:'osnutek',poslano_ob:null,odgovorjeno_ob:null,velja_do:'2026-12-06',nadomescena:false};
export const quoteFull=(state:'osnutek'|'prazen'|'poslana')=>{
 const rows=state==='prazen'?[]:quoteLines;
 const totals=state==='prazen'?{neto:'0.00',ddv:'0.00',skupaj:'0.00'}:{neto:'990.00',ddv:'217.80',skupaj:'1207.80'};
 return {...quoteBase,stanje:state==='poslana'?'poslana':'osnutek',poslano_ob:state==='poslana'?'2026-11-06T09:00:00Z':null,...totals,postavke:rows,ddv_po_stopnjah:state==='prazen'?[]:[{stopnja_ddv:'0.220000',osnova:'990.00',ddv:'217.80'}]};
};
// Customer view (PonudbaStranka): no line ids, no catalogue link, no materials; neto 810,00+180,00=990,00, DDV 178,20+39,60=217,80.
const customerLines=quoteLines.map(({id,postavka_cenika_id,materiali,...rest})=>rest);
// Stranka vidi izmere poslane različice (6x5 + 5x3 = 45 m2; 3x1 - 1x1 = 2 m2), nikoli dela, ur, delavcev ali materialov.
const snapshot=(zaporedje:number,odstej:boolean,dolzina:string,visina:string,vrednost:string)=>({zaporedje,odstej,kosi:'1.0000',dolzina,visina,sirina:null,vrednost});
const customerQuoteLines=[{...customerLines[0],izmere:[snapshot(1,false,'6.0000','5.0000','30.0000'),snapshot(2,false,'5.0000','3.0000','15.0000')]},{...customerLines[1],izmere:[snapshot(1,false,'3.0000','1.0000','3.0000'),snapshot(2,true,'1.0000','1.0000','1.0000')]}];
export const customerQuote=(state:'poslana'|'sprejeta')=>({...quoteBase,stanje:state,poslano_ob:'2026-11-06T09:00:00Z',odgovorjeno_ob:state==='sprejeta'?'2026-11-07T10:00:00Z':null,podjetje_naziv:'Mojster Novak d.o.o.',
 neto:'990.00',ddv:'217.80',skupaj:'1207.80',postavke:customerQuoteLines,ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'990.00',ddv:'217.80'}]});
// Račun: izvedena dela 990,00 neto + 217,80 DDV = 1.207,80 (isti zneski kot sprejeta ponudba P-2026-001).
export type InvoiceState = 'osnutek' | 'osnutek-pripravljen' | 'izdan' | 'placan';
export const invoice = (state: 'osnutek' | 'izdan' | 'placan') => ({ stevilka: state === 'osnutek' ? null : 'R-2026-001', stanje_dokumenta: state === 'osnutek' ? 'osnutek' : 'izdan', stanje_placila: state === 'placan' ? 'placan' : 'neplacan',
 izdajatelj_naziv: state === 'osnutek' ? null : 'Mojster Novak d.o.o.', izdajatelj_naslov: state === 'osnutek' ? null : 'Cesta 1, Maribor', izdajatelj_davcna: state === 'osnutek' ? null : 'SI12345678',
 prejemnik_naziv: state === 'osnutek' ? null : 'Janez Kranjc', prejemnik_naslov: state === 'osnutek' ? null : 'Ptuj, Slovenska 3',
 izdan_ob: state === 'osnutek' ? null : '2026-11-13T09:00:00Z', poslan_ob: state === 'osnutek' ? null : '2026-11-13T09:00:00Z', zapade_dne: state === 'osnutek' ? null : '2026-11-21', placano_ob: state === 'placan' ? '2026-11-18T10:00:00Z' : null,
 ponudba: { stevilka: 'P-2026-001', razlicica: 1 }, postavke: customerLines, ddv_po_stopnjah: [{ stopnja_ddv: '0.220000', osnova: '990.00', ddv: '217.80' }], neto: '990.00', ddv: '217.80', skupaj: '1207.80' });
export const invitations = [
 { id: 'p1', e_posta: 'nina.krajnc@example.test', stanje: 'povabljen', poslano_ob: '2026-11-05T09:00:00Z', odloceno_ob: null },
 { id: 'p2', e_posta: 'luka.bizjak@example.test', stanje: 'zavrnjeno', poslano_ob: '2026-11-02T09:00:00Z', odloceno_ob: '2026-11-03T10:00:00Z' },
 { id: 'p3', e_posta: 'tina@example.test', stanje: 'sprejeto', poslano_ob: '2026-10-28T09:00:00Z', odloceno_ob: '2026-10-29T10:00:00Z' },
 { id: 'p4', e_posta: 'stari@example.test', stanje: 'poteklo', poslano_ob: '2026-10-01T09:00:00Z', odloceno_ob: null },
 { id: 'p5', e_posta: 'napaka@example.test', stanje: 'preklicano', poslano_ob: '2026-10-20T09:00:00Z', odloceno_ob: '2026-10-21T10:00:00Z' }];
export const myInvitations = [{ id: 'p1', podjetje_id: 'c9', podjetje_naziv: 'Gradnje Kovač d.o.o.', povabil: 'Boris Kovač', poslano_ob: '2026-11-06T09:00:00Z' }];
export type Mock = { catalogStatus?: number; quote?: 'brez' | 'osnutek' | 'prazen' | 'poslana'; customerQuote?: 'poslana' | 'sprejeta'; progress?: 'termin' | 'izvedba' | 'koncana'; invoice?: InvoiceState | 'brez'; customerInvoice?: 'izdan' | 'placan'; admin?: 'napaka' | 'prazno'; workers?: 'seznam' | 'prazno' | 'napaka'; invites?: 'seznam' | 'brez'; myInvites?: boolean; items?: 'seznam' | 'prazno' | 'napaka' };
// Projekt pr3 ('Nov estrih') po stanju poteka/računa; pr6 pri stranki po stanju računa.
function masterProject(options: Mock) {
 const base = projects[2], inv = options.invoice, progress = inv === 'osnutek' ? 'izvedba' : inv === 'osnutek-pripravljen' ? 'koncana' : options.progress ?? 'izvedba';
 if (inv === 'izdan') return { ...base, faza: 'obracun', izvedba_koncana_ob: '2026-11-12T16:30:00Z' };
 if (inv === 'placan') return { ...base, faza: 'zakljucen', izvedba_koncana_ob: '2026-11-12T16:30:00Z', zakljuceno_ob: '2026-11-18T10:00:00Z' };
 if (progress === 'termin') return { ...base, faza: 'termin', termin_od: null, termin_do: null };
 return progress === 'koncana' ? { ...base, izvedba_koncana_ob: '2026-11-12T16:30:00Z' } : base;
}
export async function mockApi(page: Page, options: Mock = {}) {
 await page.route(`${SUPABASE}/**`, route => route.fulfill({ status: 200, json: {} }));
 await page.route('**/api/**', route => {
  const path = new URL(route.request().url()).pathname.replace(/^\/api/, '');
  const json = (body: unknown, status = 200) => route.fulfill({ status, json: body });
  if (path === '/config') return json({ supabase_url: SUPABASE, supabase_publishable_key: 'sb_publishable_demo' });
  if (path === '/health') return json({ status: 'ok' });
  if (path === '/me') return json(profile);
  if (path === '/podjetja') return json(companies);
  if (/^\/projekti\/[^/]+\/ponudbe$/.test(path)) return json([customerQuote(options.customerQuote ?? 'poslana')]);
  if (/^\/projekti\/[^/]+\/ponudbe\/[^/]+\/odlocitev$/.test(path)) return json(customerQuote('sprejeta'));
  if (/^\/podjetja\/.*\/projekti\/[^/]+\/ponudbe$/.test(path)) { const q = options.quote ?? 'osnutek', { postavke, ddv_po_stopnjah, ...summary } = quoteFull(q === 'brez' ? 'osnutek' : q); return json(q === 'brez' ? [] : [summary]); }
  if (/^\/podjetja\/.*\/projekti\/[^/]+\/ponudbe\/q1$/.test(path)) return json(quoteFull(options.quote === 'brez' ? 'osnutek' : (options.quote ?? 'osnutek')));
  const method = route.request().method();
  if (path === '/admin/vloge') { if (method === 'GET') return options.admin === 'napaka' ? json({ detail: 'Podatkovna baza trenutno ni na voljo.' }, 503) : json(options.admin === 'prazno' ? [] : roles); return json({}, method === 'POST' ? 201 : 200); }
  if (/^\/admin\/vloge\/[^/]+$/.test(path)) return json({});
  if (path === '/admin/podjetja' || /^\/admin\/podjetja\/[^/]+$/.test(path)) return json(companies[0], method === 'POST' ? 201 : 200);
  if (path === '/povabila') return json(options.myInvites ? myInvitations : []);
  if (path === '/povabila/p1/odlocitev') return json({ id: 'p1', stanje: route.request().postDataJSON().sprejmi ? 'sprejeto' : 'zavrnjeno' });
  if (/^\/podjetja\/[^/]+\/delavci\/povabila$/.test(path)) {
   if (method === 'POST') return route.request().postDataJSON().e_posta === 'napaka@example.test' ? json({ detail: 'Preveč povabil. Poskusite pozneje.' }, 429) : json({ id: 'p9', e_posta: route.request().postDataJSON().e_posta, stanje: 'povabljen', poslano_ob: '2026-11-07T09:00:00Z' }, 201);
   return json(options.invites === 'brez' ? [] : invitations);
  }
  if (/^\/podjetja\/[^/]+\/delavci\/povabila\/[^/]+\/preklic$/.test(path)) return json({ ...invitations[0], stanje: 'preklicano' });
  if (/^\/podjetja\/[^/]+\/delavci$/.test(path)) {
   return options.workers === 'napaka' ? json({ detail: 'Podatkovna baza trenutno ni na voljo.' }, 503) : json(options.workers === 'prazno' ? [] : workers);
  }
  if (/^\/podjetja\/[^/]+\/delavci\/[^/]+$/.test(path)) return json({});
  if (/^\/podjetja\/[^/]+\/vrste-dela$/.test(path)) return method === 'POST' ? json(trades[0], 201) : json(trades);
  if (/^\/podjetja\/[^/]+\/projekti\/[^/]+\/postavke$/.test(path)) { if (method !== 'GET') return json({}, 201); return options.items === 'napaka' ? json({ detail: 'Podatkovna baza trenutno ni na voljo.' }, 503) : json(options.items === 'prazno' ? { postavke: [], neto: '0.00', ddv: '0.00', skupaj: '0.00' } : projectItems); }
  if (/^\/podjetja\/[^/]+\/projekti\/[^/]+\/postavke\/[^/]+(\/izmere(\/[^/]+)?|\/iz-cenika)?$/.test(path)) return json({});
  if (/^\/podjetja\/[^/]+\/vrste-dela\/[^/]+(\/materiali\/[^/]+)?$/.test(path)) return json({}, method === 'POST' ? 201 : 200);
  if (/^\/projekti\/[^/]+\/racun$/.test(path)) return options.customerInvoice ? json(invoice(options.customerInvoice)) : json({ detail: 'Zapis ni na voljo.' }, 404);
  if (/^\/podjetja\/.*\/projekti\/[^/]+\/(termin|izvedba)$/.test(path)) return json(masterProject(options));
  if (/^\/podjetja\/.*\/projekti\/[^/]+\/racun$/.test(path)) return options.invoice && options.invoice !== 'brez' ? json(invoice(options.invoice === 'osnutek-pripravljen' ? 'osnutek' : options.invoice)) : json({ detail: 'Zapis ni na voljo.' }, 404);
  if (/^\/podjetja\/.*\/projekti\/[^/]+\/racun\/(izdaj|placilo)$/.test(path)) return json(invoice(path.endsWith('izdaj') ? 'izdan' : 'placan'));
  if (path === '/projekti') return json(options.customerInvoice === 'placan' ? ownProjects.map(x => x.id === 'pr6' ? { ...x, faza: 'zakljucen', zakljuceno_ob: '2026-11-18T10:00:00Z' } : x) : ownProjects);
  if (path.endsWith('/projekti')) return json(projects.map(x => x.id === 'pr3' ? masterProject(options) : x));
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

// Stateful walk-through (#51): projekt -> ponudba -> pošiljanje -> sprejem stranke -> termin -> izvedba -> račun -> plačilo.
// Zneski: 1 postavka, 8 m2 x 125,00 = 1.000,00 neto, 22 % DDV = 220,00, skupaj 1.220,00.
export async function mockFlow(page: Page) {
 await mockApi(page);
 const s = { created: false, faza: 'pregled', quote: null as null | 'osnutek' | 'poslana' | 'sprejeta', lines: false, item: false, edited: false, termin: false, koncana: false, invoice: 'osnutek' as 'osnutek' | 'izdan' | 'placan', rec: null as null | { prejemnik_naziv: string; prejemnik_naslov: string; zapade_dne: string } };
 const line = { id: 'fl1', postavka_cenika_id: null, zaporedje: 1, naziv: 'Beljenje sten', opis: 'Dve plasti', vrsta_dela: 'Beljenje', enota: 'm2', cena_na_enoto: '125.0000', kolicina: '1.0000', izmera_skupaj: '8.0000', popust: '0.000000', stopnja_ddv: '0.220000', neto: '1000.00', ddv: '220.00', koncna_cena: '1220.00', materiali: [] };
 const itemRow = () => ({ ...itemBase, id: 'fi1', zaporedje: 1, naziv: 'Beljenje sten', opis: 'Dve plasti', vrsta_dela_id: 'v4', vrsta_dela: 'Beljenje', enota: 'm2', cena_na_enoto: '125.0000', izmera_skupaj: s.lines ? '8.0000' : '0.0000', neto: s.lines ? '1000.00' : '0.00', ddv: s.lines ? '220.00' : '0.00', koncna_cena: s.lines ? '1220.00' : '0.00', izmere: s.lines ? [{ id: 'fz1', zaporedje: 1, odstej: false, kosi: '1.0000', dolzina: '4.0000', visina: '2.0000', sirina: null, vrednost: '8.0000' }] : [] });
 const quote = () => ({ id: 'fq1', stevilka: 'P-2026-002', razlicica: 1, stanje: s.quote ?? 'osnutek', poslano_ob: s.quote && s.quote !== 'osnutek' ? '2026-11-06T09:00:00Z' : null, odgovorjeno_ob: s.quote === 'sprejeta' ? '2026-11-07T10:00:00Z' : null, velja_do: '2026-12-06', nadomescena: false,
  neto: s.lines ? '1000.00' : '0.00', ddv: s.lines ? '220.00' : '0.00', skupaj: s.lines ? '1220.00' : '0.00', postavke: s.lines ? [line] : [], ddv_po_stopnjah: s.lines ? [{ stopnja_ddv: '0.220000', osnova: '1000.00', ddv: '220.00' }] : [] });
 const summary = () => { const { postavke, ddv_po_stopnjah, ...rest } = quote(); return rest; };
 const stranka = () => { const { id, postavke, ...rest } = quote(); return { id, ...rest, podjetje_naziv: 'Mojster Novak d.o.o.', postavke: postavke.map(({ id: _id, postavka_cenika_id, materiali, ...l }) => l) }; };
 const term = s.termin ? { termin_od: '2026-11-10T08:00:00Z', termin_do: '2026-11-11T16:00:00Z' } : { termin_od: null, termin_do: null };
 const master = () => ({ id: 'pf1', naziv: 'Prenova kuhinje', opis: 'Beljenje po prenovi', lokacija_izvedbe: 'Maribor, Glavni trg 1', faza: s.faza, stranka_ime: 'Janez', stranka_priimek: 'Kranjc', stranka_e_posta: 'janez@example.test',
  ...(s.termin ? { termin_od: '2026-11-10T08:00:00Z', termin_do: '2026-11-11T16:00:00Z' } : term), izvedba_koncana_ob: s.koncana ? '2026-11-11T16:30:00Z' : null, zakljuceno_ob: s.faza === 'zakljucen' ? '2026-11-18T10:00:00Z' : null });
 const own = () => { const { stranka_ime, stranka_priimek, stranka_e_posta, ...rest } = master(); return { ...rest, podjetje_naziv: 'Mojster Novak d.o.o.' }; };
 const racun = () => ({ ...invoice(s.invoice), prejemnik_naziv: s.invoice === 'osnutek' ? null : s.rec?.prejemnik_naziv ?? 'Janez Kranjc', prejemnik_naslov: s.invoice === 'osnutek' ? null : s.rec?.prejemnik_naslov ?? 'Maribor, Glavni trg 1',
  ponudba: { stevilka: 'P-2026-002', razlicica: 1 }, neto: '1000.00', ddv: '220.00', skupaj: '1220.00', ddv_po_stopnjah: [{ stopnja_ddv: '0.220000', osnova: '1000.00', ddv: '220.00' }],
  postavke: [{ zaporedje: 1, naziv: 'Beljenje sten', opis: 'Dve plasti', vrsta_dela: 'Beljenje', enota: 'm2', cena_na_enoto: '125.0000', kolicina: '8.0000', popust: '0.000000', stopnja_ddv: '0.220000', neto: '1000.00', ddv: '220.00', koncna_cena: '1220.00' }] });
 const base = `/podjetja/${A}/projekti`;
 await page.route('**/api/**', route => {
  const path = new URL(route.request().url()).pathname.replace(/^\/api/, ''), method = route.request().method();
  const json = (body: unknown, status = 200) => route.fulfill({ status, json: body });
  const missing = () => json({ detail: 'Zapis ni na voljo.' }, 404);
  if (path === base) { if (method === 'POST') { s.created = true; return json(master(), 201); } return json(s.created ? [master()] : []); }
  if (path === '/projekti') return json(s.created ? [own()] : []);
  if (!path.includes('/pf1') && !path.includes('/projekti/pf1')) return route.fallback();
  if (path === `${base}/pf1/ponudbe`) { if (method === 'POST') { s.quote = 'osnutek'; return json(quote(), 201); } return json(s.quote ? [summary()] : []); }
  if (path === `${base}/pf1/ponudbe/fq1`) return json(quote());
  if (path === `${base}/pf1/postavke`) { if (method === 'POST') { s.item = true; return json(itemRow(), 201); } return json({ postavke: s.item ? [itemRow()] : [], neto: s.lines ? '1000.00' : '0.00', ddv: s.lines ? '220.00' : '0.00', skupaj: s.lines ? '1220.00' : '0.00' }); }
  if (path === `${base}/pf1/postavke/fi1`) { if (method === 'PUT') s.edited = true; return json(itemRow()); }
  if (path === `${base}/pf1/postavke/fi1/izmere`) { s.lines = true; return json({}, 201); }
  if (path === `${base}/pf1/ponudbe/fq1/poslji`) { s.quote = 'poslana'; s.faza = 'ponudba'; return json(quote()); }
  if (path === '/projekti/pf1/ponudbe') return json(s.quote && s.quote !== 'osnutek' ? [stranka()] : []);
  if (path === '/projekti/pf1/ponudbe/fq1/odlocitev') { s.quote = 'sprejeta'; s.faza = 'termin'; return json(stranka()); }
  if (path === `${base}/pf1/termin`) { s.termin = true; s.faza = 'izvedba'; return json(master()); }
  if (path === `${base}/pf1/izvedba`) { s.koncana = true; return json(master()); }
  if (path === `${base}/pf1/racun`) return s.quote === 'sprejeta' ? json(racun()) : missing();
  if (path === `${base}/pf1/racun/izdaj`) { s.rec = route.request().postDataJSON(); s.invoice = 'izdan'; s.faza = 'obracun'; return json(racun()); }
  if (path === `${base}/pf1/racun/placilo`) { s.invoice = 'placan'; s.faza = 'zakljucen'; return json(racun()); }
  if (path === '/projekti/pf1/racun') return s.invoice === 'osnutek' ? missing() : json(racun());
  return route.fallback();
 });
}
