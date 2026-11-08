import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { render, expectToast } from './render';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import Admin from '../features/administration/components/Admin';
import { api } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...await importOriginal<typeof import('../services/api')>(), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
// Podjetja: A aktivno (lastnik Ana), B aktivno (lastnik Cene), C neaktivno.
const companies=[
 {id:'A',lastnik_id:'u1',naziv:'Gradnje d.o.o.',maticna_stevilka:'1234567',davcna_stevilka:null,naslov:'Cesta 1, Maribor',aktivno:true},
 {id:'B',lastnik_id:'u3',naziv:'Zidar s.p.',maticna_stevilka:'7654321',davcna_stevilka:null,naslov:'Ulica 2, Celje',aktivno:true},
 {id:'C',lastnik_id:'u2',naziv:'Parket Plus',maticna_stevilka:'1111111',davcna_stevilka:null,naslov:'Trg 3, Kranj',aktivno:false},
];
const users=[
 {id:'u1',e_posta:'ana@gradnje.si',ime:'Ana',priimek:'Novak',potrjen:true},
 {id:'u2',e_posta:'boris@mail.si',ime:'Boris',priimek:'Kos',potrjen:true},
 {id:'u3',e_posta:'cene@mail.si',ime:'Cene',priimek:'Zor',potrjen:true},
 {id:'u4',e_posta:'skrbnik@quoteflow.si',ime:'Sara',priimek:'Admin',potrjen:true},
 {id:'u5',e_posta:'neznan@mail.si',ime:'Neznan',priimek:'Uporabnik',potrjen:false},
 {id:'u6',e_posta:'prazen@mail.si',ime:'Peter',priimek:'Prazen',potrjen:true},
];
const row=(id:string,u:string,podjetje:string|null,vloga:string,aktivna:boolean,more={})=>{const x=users.find(y=>y.id===u)!;const c=companies.find(y=>y.id===podjetje);
 return {id,uporabnik_id:u,e_posta:x.e_posta,ime:x.ime,priimek:x.priimek,podjetje_id:podjetje,naziv:c?.naziv??null,vloga,aktivna,je_lastnik:false,dodeljeno_ob:'2026-11-03T09:00:00Z',...more};};
const initial=()=>[
 row('r1','u4',null,'admin',true),
 row('r2','u1','A','mojster',true,{je_lastnik:true}),
 row('r3','u2','A','delavec',true),
 row('r4','u3','A','delavec',false),
 row('r5','u2','B','delavec',false),
 row('r6','u2',null,'stranka',true),
 row('r7','u3','B','mojster',true,{je_lastnik:true}),
];
const applications=[{id:'p1',uporabnik_id:'u2',naziv_podjetja:'Elektro Kos d.o.o.',maticna_stevilka:'6667890000',davcna_stevilka:null,naslov_podjetja:'Ulica 2, Celje',stanje:'oddana',podjetje_id:null,oddano_ob:'2026-11-03T10:15:00Z',odloceno_ob:null,e_posta:'boris@mail.si',ime:'Boris',priimek:'Kos'}];
let roles:ReturnType<typeof initial>;let failure:Error|null;let loadFailures:number;
beforeEach(()=>{vi.clearAllMocks();roles=initial();failure=null;loadFailures=0;
 mockedApi.mockImplementation(async(_c,path,method,body)=>{
  if(!method&&loadFailures>0&&path==='/admin/vloge'){loadFailures--;throw new Error('Podatkovna baza trenutno ni na voljo.');}
  if(!method){if(path==='/podjetja')return companies;if(path==='/admin/uporabniki')return users;if(path==='/admin/vloge')return roles;if(path==='/admin/prosnje')return applications;return [];}
  if(failure)throw failure;
  if(method==='PATCH'){const id=path.split('/').at(-1);roles=roles.map(r=>r.id===id?{...r,aktivna:(body as {aktivna:boolean}).aktivna}:r);return {};}
  return {};
 });
});
const open=async()=>{render(<Admin client={client}/>);await screen.findByRole('tablist');};
const patches=()=>mockedApi.mock.calls.filter(c=>c[2]==='PATCH');
const posts=()=>mockedApi.mock.calls.filter(c=>c[2]==='POST');
const pick=(name:RegExp|string)=>userEvent.click(screen.getByRole('button',{name}));
const members=()=>screen.getByRole('table',{name:/Člani/});
const memberRow=(email:string)=>within(members()).getByRole('row',{name:new RegExp(email.replace('.','\\.'))});
async function company(name='Gradnje d.o.o.'){await open();await pick(new RegExp('^'+name.replace('.','\\.')));await screen.findByRole('table',{name:/Člani/});}
const select=(label:string,option:string)=>userEvent.selectOptions(screen.getByLabelText(label),option);

describe('Administracija: zavihki',()=>{
 it('naslov in štirje zavihki, privzeto Po podjetjih',async()=>{
  await open();expect(screen.getByRole('heading',{level:1,name:'Podjetja in pravice'})).toBeTruthy();
  const tabs=within(screen.getByRole('tablist')).getAllByRole('tab');
  expect(tabs.map(t=>t.textContent!.replace(/\s+/g,' ').trim())).toEqual(['Po podjetjih','Po uporabnikih',expect.stringMatching(/^Prošnje mojstrov/),'Podjetja']);
  expect(screen.getByRole('tab',{name:'Po podjetjih'}).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('tabpanel')).toBeTruthy();
 });
 it('zavihek prošenj kaže število oddanih prošenj',async()=>{await open();expect(screen.getByRole('tab',{name:/^Prošnje mojstrov/}).textContent).toMatch(/\(1\)/);});
 it('puščici na tipkovnici premakneta izbiro zavihka',async()=>{
  await open();screen.getByRole('tab',{name:'Po podjetjih'}).focus();await userEvent.keyboard('{ArrowRight}');
  expect(screen.getByRole('tab',{name:'Po uporabnikih'}).getAttribute('aria-selected')).toBe('true');
  await userEvent.keyboard('{ArrowLeft}');expect(screen.getByRole('tab',{name:'Po podjetjih'}).getAttribute('aria-selected')).toBe('true');
 });
 it('med nalaganjem pokaže stanje nalaganja, ob napaki opozorilo in poskusi znova',async()=>{
  loadFailures=1;render(<Admin client={client}/>);
  expect(screen.getAllByRole('status').map(s=>s.textContent).join(' ')).toContain('Nalagam podatke …');
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');
  expect(screen.queryByRole('tablist')).toBeNull();
  await pick('Poskusi znova');expect(await screen.findByRole('tablist')).toBeTruthy();expect(screen.queryByRole('alert')).toBeNull();
 });
});

describe('Po podjetjih',()=>{
 it('seznam podjetij s štetjem, iskanjem in pozivom k izbiri',async()=>{
  await open();expect(screen.getByText('3 podjetja')).toBeTruthy();expect(screen.getByText('Izberite podjetje na levi.')).toBeTruthy();
  await userEvent.type(screen.getByLabelText('Poišči podjetje'),'PARKET');
  expect(screen.queryByRole('button',{name:/^Gradnje/})).toBeNull();expect(screen.getByRole('button',{name:/^Parket Plus/})).toBeTruthy();expect(screen.getByText('1 podjetje')).toBeTruthy();
 });
 it('iskanje podjetja po matični številki in brez zadetkov ponudi počisti iskanje',async()=>{
  await open();await userEvent.type(screen.getByLabelText('Poišči podjetje'),'7654321');expect(screen.getByRole('button',{name:/^Zidar s\.p\./})).toBeTruthy();
  await userEvent.clear(screen.getByLabelText('Poišči podjetje'));await userEvent.type(screen.getByLabelText('Poišči podjetje'),'abc');
  expect(screen.getByText('Ni zadetkov za »abc«.')).toBeTruthy();await pick('Počisti iskanje');expect(screen.getByRole('button',{name:/^Gradnje/})).toBeTruthy();
 });
 it('izbrano podjetje pokaže lastnika in privzeto samo aktivne člane',async()=>{
  await company();expect(screen.getByRole('heading',{name:'Gradnje d.o.o.'})).toBeTruthy();expect(screen.getByText(/Lastnik: ana@gradnje\.si/)).toBeTruthy();
  expect(within(members()).getByText('boris@mail.si')).toBeTruthy();expect(within(members()).getByText('ana@gradnje.si')).toBeTruthy();expect(within(members()).queryByText('cene@mail.si')).toBeNull();
  expect(screen.getByText('2 člana')).toBeTruthy();expect((screen.getByLabelText('Stanje') as HTMLSelectElement).value).toBe('aktivne');
 });
 it('filter stanja Odvzete in Vse spremeni vrstice in štetje',async()=>{
  await company();await select('Stanje','Odvzete');expect(within(members()).getByText('cene@mail.si')).toBeTruthy();expect(within(members()).queryByText('boris@mail.si')).toBeNull();expect(screen.getByText('1 član')).toBeTruthy();
  await select('Stanje','Vse');expect(screen.getByText('3 člani')).toBeTruthy();
 });
 it('filter vloge in iskanje člana po e-pošti brez ozira na velikost črk',async()=>{
  await company();await select('Vloga','Delavec');expect(within(members()).queryByText('ana@gradnje.si')).toBeNull();expect(screen.getByText('1 član')).toBeTruthy();
  await select('Vloga','Vse vloge');await userEvent.type(screen.getByLabelText('Poišči člana'),'BORIS');expect(screen.getByText('1 član')).toBeTruthy();expect(within(members()).getByText('boris@mail.si')).toBeTruthy();
 });
 it('brez ujemanja pove, da ni članov, in počisti filtre',async()=>{
  await company();await userEvent.type(screen.getByLabelText('Poišči člana'),'nihče');
  expect(screen.getByText('Ni članov, ki ustrezajo filtrom.')).toBeTruthy();await pick('Počisti filtre');
  expect(within(members()).getByText('boris@mail.si')).toBeTruthy();expect((screen.getByLabelText('Poišči člana') as HTMLInputElement).value).toBe('');
 });
 it('odvzem ima besedilni gumb z imenom osebe in vloge ter najprej vpraša',async()=>{
  await company();const button=within(memberRow('boris@mail.si')).getByRole('button',{name:'Odvzemi vlogo Delavec uporabniku boris@mail.si'});
  expect(button.textContent).toMatch(/Odvzemi/);expect(button.querySelector('svg')).toBeTruthy();
  await userEvent.click(button);expect(patches()).toHaveLength(0);
  expect(screen.getByText('Odvzamem vlogo Delavec uporabniku boris@mail.si pri podjetju Gradnje d.o.o.?')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Odvzemi vlogo'})).toBeTruthy();expect(screen.getByRole('button',{name:'Prekliči'})).toBeTruthy();
 });
 it('prekliči odvzema ne pošlje ničesar',async()=>{
  await company();await pick('Odvzemi vlogo Delavec uporabniku boris@mail.si');await pick('Prekliči');
  expect(patches()).toHaveLength(0);expect(screen.queryByRole('button',{name:'Odvzemi vlogo'})).toBeNull();expect(screen.getByRole('button',{name:'Odvzemi vlogo Delavec uporabniku boris@mail.si'})).toBeTruthy();
 });
 it('potrjen odvzem pošlje PATCH, osveži in sporoči uspeh brez vrstice',async()=>{
  await company();await pick('Odvzemi vlogo Delavec uporabniku boris@mail.si');await pick('Odvzemi vlogo');
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/vloge/r3','PATCH',{aktivna:false}));
  await expectToast('Vloga je odvzeta.');
  await waitFor(()=>expect(within(members()).queryByText('boris@mail.si')).toBeNull());
 });
 it('ponovna aktivacija odvzete vloge ne zahteva potrditve',async()=>{
  await company();await select('Stanje','Odvzete');
  await pick(/Ponovno aktiviraj.*cene@mail\.si/);
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/vloge/r4','PATCH',{aktivna:true}));
  await expectToast('Vloga je ponovno aktivna.');
 });
 it('lastnik ima onemogočen odvzem z vidno razlago, odvzem ne pošlje ničesar',async()=>{
  await company();const r=memberRow('ana@gradnje.si');
  expect(within(r).getByText('Lastnik')).toBeTruthy();
  const button=within(r).getByRole('button',{name:/Odvzemi.*ana@gradnje\.si/}) as HTMLButtonElement;expect(button.disabled).toBe(true);
  expect(screen.getByText('Lastnik ne more izgubiti vloge mojster. Najprej zamenjajte lastnika.')).toBeTruthy();
  await userEvent.click(button);expect(patches()).toHaveLength(0);
 });
 it('napaka pri odvzemu pokaže opozorilo, vrstica ostane in gumb je znova omogočen',async()=>{
  await company();failure=new Error('Lastnik potrebuje aktivno vlogo mojster pri svojem podjetju.');
  await pick('Odvzemi vlogo Delavec uporabniku boris@mail.si');await pick('Odvzemi vlogo');
  expect((await screen.findByRole('alert')).textContent).toContain('Lastnik potrebuje aktivno vlogo mojster');
  expect(within(members()).getByText('boris@mail.si')).toBeTruthy();expect(screen.queryByText('Vloga je odvzeta.')).toBeNull();
  expect((screen.getByRole('button',{name:'Odvzemi vlogo Delavec uporabniku boris@mail.si'}) as HTMLButtonElement).disabled).toBe(false);
 });
 it('dodaj člana odpre predal, ki ne ponuja že aktivnih, nepotrjenih ali skrbnikov',async()=>{
  await company();await pick('Dodaj člana');const d=within(await screen.findByRole('dialog'));
  const options=within(d.getByLabelText('Uporabnik')).getAllByRole('option') as HTMLOptionElement[];const text=options.map(o=>o.textContent);
  expect(text.some(t=>t!.includes('cene@mail.si'))).toBe(true);expect(text.some(t=>t!.includes('boris@mail.si'))).toBe(false);expect(text.some(t=>t!.includes('neznan@mail.si'))).toBe(false);
  expect(options.find(o=>o.textContent!.includes('skrbnik@quoteflow.si'))!.disabled).toBe(true);expect(d.getByText('Skrbnik si ne more sam dodeliti vloge v podjetju.')).toBeTruthy();
  expect((d.getByRole('radio',{name:/Delavec/}) as HTMLInputElement).checked).toBe(true);expect(d.getByRole('radio',{name:/Mojster/})).toBeTruthy();expect(d.queryByRole('radio',{name:/Stranka/})).toBeNull();
 });
 it('dodelitev v predalu pošlje POST z izbranim podjetjem in vlogo ter sporoči uspeh',async()=>{
  await company();await pick('Dodaj člana');const d=within(await screen.findByRole('dialog'));
  await userEvent.selectOptions(d.getByLabelText('Uporabnik'),'u6');await userEvent.click(d.getByRole('button',{name:'Dodeli vlogo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/vloge','POST',{uporabnik_id:'u6',podjetje_id:'A',vloga:'delavec'}));
  await expectToast('Vloga je dodeljena.');
 });
 it('neaktivno podjetje ne dovoli dodajanja članov in pove razlog',async()=>{
  await company('Parket Plus');expect((screen.getByRole('button',{name:'Dodaj člana'}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText('Podjetje je neaktivno. Najprej ga aktivirajte.')).toBeTruthy();
 });
 it('podjetje brez članov pove, da ni članov',async()=>{
  roles=roles.filter(r=>r.podjetje_id!=='A');await open();await pick(/^Gradnje/);expect(await screen.findByText('Ni članov, ki ustrezajo filtrom.')).toBeTruthy();
 });
});

describe('Po uporabnikih',()=>{
 const user=async(name:string)=>{await open();await userEvent.click(screen.getByRole('tab',{name:'Po uporabnikih'}));await pick(new RegExp('^'+name));};
 it('iskanje uporabnika po e-pošti in izbira pokažeta glavo z globalnimi vlogami',async()=>{
  await open();await userEvent.click(screen.getByRole('tab',{name:'Po uporabnikih'}));expect(screen.getByText('Izberite uporabnika na levi.')).toBeTruthy();
  await userEvent.type(screen.getByLabelText('Poišči uporabnika'),'BORIS@');expect(screen.queryByRole('button',{name:/^Ana Novak/})).toBeNull();
  await pick(/^Boris Kos/);expect(screen.getByRole('heading',{name:/Boris Kos/})).toBeTruthy();
  expect(within(screen.getByRole('group',{name:'Globalno'})).getByText('Stranka')).toBeTruthy();
 });
 it('vloge so združene po podjetjih in privzeto brez odvzetih',async()=>{
  await user('Boris Kos');const card=screen.getByRole('group',{name:'Gradnje d.o.o.'});
  expect(within(card).getByText(/Delavec/)).toBeTruthy();expect(within(card).getByText('Aktivna')).toBeTruthy();expect(screen.queryByRole('group',{name:'Zidar s.p.'})).toBeNull();
  await select('Stanje','Vse');expect(within(screen.getByRole('group',{name:'Zidar s.p.'})).getByRole('button',{name:/Ponovno aktiviraj/})).toBeTruthy();
 });
 it('odvzem pri uporabniku ima isti postopek s potrditvijo',async()=>{
  await user('Boris Kos');await pick('Odvzemi vlogo Delavec uporabniku boris@mail.si');expect(patches()).toHaveLength(0);
  expect(screen.getByText('Odvzamem vlogo Delavec uporabniku boris@mail.si pri podjetju Gradnje d.o.o.?')).toBeTruthy();await pick('Odvzemi vlogo');
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/vloge/r3','PATCH',{aktivna:false}));
 });
 it('lastnik podjetja ne more izgubiti vloge mojster in skrbnikova vloga nima odvzema',async()=>{
  await user('Cene Zor');expect((within(screen.getByRole('group',{name:'Zidar s.p.'})).getByRole('button',{name:/Odvzemi.*cene@mail\.si/}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText('Lastnik podjetja Zidar s.p. ne more izgubiti vloge mojster.')).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:/^Sara Admin/}));expect(screen.getByText('Skrbnik')).toBeTruthy();
  expect(screen.queryByRole('button',{name:/Odvzemi.*skrbnik@quoteflow\.si/})).toBeNull();
 });
 it('uporabnik brez poslovnih vlog pokaže prazno stanje',async()=>{await user('Peter Prazen');expect(screen.getByText('Uporabnik nima poslovnih vlog.')).toBeTruthy();});
 it('dodeli vlogo pošlje podjetje in vlogo izbranega uporabnika',async()=>{
  await user('Peter Prazen');await pick('Dodeli vlogo');const d=within(await screen.findByRole('dialog'));
  await userEvent.selectOptions(d.getByLabelText('Podjetje'),'B');await userEvent.click(d.getByRole('radio',{name:/Mojster/}));await userEvent.click(d.getByRole('button',{name:'Dodeli vlogo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/vloge','POST',{uporabnik_id:'u6',podjetje_id:'B',vloga:'mojster'}));
 });
 it('ime podjetja v kartici odpre to podjetje v pogledu Po podjetjih',async()=>{
  await user('Boris Kos');await pick('Odpri podjetje Gradnje d.o.o.');
  expect(screen.getByRole('tab',{name:'Po podjetjih'}).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('heading',{name:'Gradnje d.o.o.'})).toBeTruthy();expect(screen.getByRole('table',{name:/Člani/})).toBeTruthy();
 });
});

describe('Prošnje mojstrov in Podjetja pod zavihki',()=>{
 it('zavihek prošenj ohrani odločanje z gumbi Odobri in Zavrni',async()=>{
  await open();await userEvent.click(screen.getByRole('tab',{name:/^Prošnje mojstrov/}));
  expect(within(screen.getByRole('tabpanel')).getByText('boris@mail.si')).toBeTruthy();await pick('Odobri Elektro Kos d.o.o.');
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/admin/prosnje/p1/odlocitev','POST',{odobri:true}));
 });
 it('obrazec podjetja je skrit za gumbom Dodaj podjetje in odpre predal',async()=>{
  await open();await userEvent.click(screen.getByRole('tab',{name:'Podjetja'}));
  expect(screen.queryByLabelText('Naziv podjetja')).toBeNull();expect(screen.getAllByRole('button',{name:/^Uredi /}).length).toBe(3);
  await pick('Dodaj podjetje');const d=within(await screen.findByRole('dialog'));
  for(const label of ['Naziv podjetja','Lastnik podjetja','Matična številka','Davčna številka','Naslov podjetja'])expect(d.getByLabelText(label)).toBeTruthy();
 });
 it('urejanje podjetja v predalu pošlje PUT',async()=>{
  await open();await userEvent.click(screen.getByRole('tab',{name:'Podjetja'}));await pick('Uredi Zidar s.p.');
  const d=within(await screen.findByRole('dialog'));expect((d.getByLabelText('Naziv podjetja') as HTMLInputElement).value).toBe('Zidar s.p.');
  await userEvent.click(d.getByRole('button',{name:'Shrani spremembe'}));
  await waitFor(()=>expect(mockedApi.mock.calls.some(c=>c[1]==='/admin/podjetja/B'&&c[2]==='PUT')).toBe(true));
 });
});
