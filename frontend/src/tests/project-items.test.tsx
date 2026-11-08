import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import ProjectItems from '../features/items/components/ProjectItems';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...await importOriginal<typeof import('../services/api')>(), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const pickMenu=async(proj:string,item:string)=>{await userEvent.click(await screen.findByRole('button',{name:`Več dejanj ${proj}`}));await userEvent.click(await screen.findByRole('menuitem',{name:item}))};
const P='/podjetja/a/projekti/p1/postavke';
const money=(re:string)=>new RegExp(re.replace('.','\\.')+'\\s?€');
// Primer iz G1: izmere 5x4 m2 + 2x1 m2 - 1x2 m2 = 20 m2; 20 x 1 x 10 EUR + 25 EUR x 8 h x 2 delavca = 600; popust 10 % -> 540,00; DDV 118,80; skupaj 658,80.
const izmera=(id:string,zaporedje:number,odstej:boolean,kosi:string,dolzina:string,visina:string|null,vrednost:string)=>({id,zaporedje,odstej,kosi,dolzina,visina,sirina:null,vrednost});
const item=(id:string,naziv:string,enota:string,more={})=>({id,zaporedje:1,naziv,opis:'Opis',vrsta_dela_id:'v1',vrsta_dela:'Keramika',enota,cena_na_enoto:'0.0000',kolicina:'1.0000',popust:'0.000000',stopnja_ddv:'0.220000',urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,izmera_skupaj:'0.0000',cena_dela:'0.00',neto:'0.00',ddv:'0.00',koncna_cena:'0.00',izmere:[] as unknown[],...more});
const main=()=>item('i1','Polaganje keramike','m2',{cena_na_enoto:'10.0000',popust:'0.100000',urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,izmera_skupaj:'20.0000',cena_dela:'400.00',neto:'540.00',ddv:'118.80',koncna_cena:'658.80',
 izmere:[izmera('z1',1,false,'1.0000','5.0000','4.0000','20.0000'),izmera('z2',2,false,'1.0000','2.0000','1.0000','2.0000'),izmera('z3',3,true,'1.0000','1.0000','2.0000','2.0000')]});
const initial=()=>({postavke:[main(),item('i2','Polaganje roba','m'),item('i3','Zasip','m3'),item('i4','Montaža vrat','kos')],neto:'540.00',ddv:'118.80',skupaj:'658.80'});
const trades=[
 {id:'v1',naziv:'Keramika',opis:'',urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,aktivna:true,cena_dela:'400.00',materiali:[]},
 {id:'v2',naziv:'Beljenje',opis:'',urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,aktivna:true,cena_dela:'0.00',materiali:[]},
 {id:'v3',naziv:'Staro delo',opis:'',urna_postavka:'1.0000',stevilo_ur:'1.0000',stevilo_delavcev:1,aktivna:false,cena_dela:'1.00',materiali:[]},
];
const catalog=[{id:'c1',podjetje_id:'a',naziv:'Rušenje estriha',opis:'x',vrsta_dela:'Rušenje',vrsta_dela_id:'v2',enota:'m2',cena_na_enoto:'12.4500',stopnja_ddv:'0.22',aktivna:true}];
let data:ReturnType<typeof initial>;let failure:Error|null;
beforeEach(()=>{vi.clearAllMocks();data=initial();failure=null;
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(!method){if(path===P)return data;if(path==='/podjetja/a/vrste-dela')return trades;if(path==='/podjetja/a/cenik')return catalog;return [];}
  if(failure)throw failure;return {};
 });
});
const open=async()=>{render(<ProjectItems client={client} companyId="a" projectId="p1"/>);await screen.findByText('Polaganje keramike');};
const writes=()=>mockedApi.mock.calls.filter(c=>c[2]);
const dialog=async()=>within(await screen.findByRole('dialog'));
const pick=(name:RegExp|string)=>userEvent.click(screen.getByRole('button',{name}));
const fill=async(d:ReturnType<typeof within>,label:string,value:string)=>{const el=d.getByLabelText(label);await userEvent.clear(el);await userEvent.type(el,value);};

describe('Postavke projekta: seznam',()=>{
 it('tabela pokaže vrsto dela, skupno izmero, neto in končno ceno, vsote v skupini',async()=>{
  await open();const row=screen.getByRole('row',{name:/Polaganje keramike/});
  expect(row.textContent).toContain('Keramika');expect(row.textContent).toMatch(/20\s?m²/);expect(row.textContent).toMatch(money('540,00'));expect(row.textContent).toMatch(money('658,80'));
  expect(screen.getByRole('table',{name:/Postavke projekta/})).toBeTruthy();
  const totals=screen.getByRole('group',{name:'Vsote postavk'});for(const a of ['540,00','118,80','658,80'])expect(totals.textContent).toMatch(money(a));
  expect(mockedApi).toHaveBeenCalledWith(client,P);
 });
 it('postavka brez izmer je označena, ker je pošiljanje ne dovoli',async()=>{
  await open();expect(screen.getByRole('row',{name:/Polaganje roba/}).textContent).toMatch(/Brez izmer/);expect(screen.getByRole('row',{name:/Polaganje keramike/}).textContent).not.toMatch(/Brez izmer/);
 });
 it('brez postavk pokaže prazno stanje in gumb Nova postavka',async()=>{
  data={postavke:[],neto:'0.00',ddv:'0.00',skupaj:'0.00'};render(<ProjectItems client={client} companyId="a" projectId="p1"/>);
  expect(await screen.findByText('Projekt še nima postavk.')).toBeTruthy();expect(screen.getByRole('button',{name:'Nova postavka'})).toBeTruthy();
 });
 it('napaka pri nalaganju pokaže opozorilo brez praznega stanja',async()=>{
  mockedApi.mockRejectedValue(new Error('Podatkovna baza trenutno ni na voljo.'));render(<ProjectItems client={client} companyId="a" projectId="p1"/>);
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText('Projekt še nima postavk.')).toBeNull();
 });
 it('odstrani postavko pošlje DELETE na postavko',async()=>{
  await open();await pick('Odstrani Polaganje keramike');await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i1','DELETE'));
 });
});

describe('Postavke projekta: obrazec postavke',()=>{
 it('vsebuje polja postavke in dela, brez polj izmer; količina je privzeto 1',async()=>{
  await open();await pick('Nova postavka');const d=await dialog();
  for(const l of ['Naziv','Opis','Vrsta dela','Enota','Cena na enoto','Količina','Popust (%)','Stopnja DDV (%)','Urna postavka (€)','Število ur','Število delavcev'])expect(d.getByLabelText(l)).toBeTruthy();
  expect((d.getByLabelText('Količina') as HTMLInputElement).value).toBe('1');
  for(const l of ['Dolžina','Višina','Širina','Kosi'])expect(d.queryByLabelText(l)).toBeNull();
  expect(within(d.getByLabelText('Enota')).getAllByRole('option').map(o=>o.textContent)).toEqual(expect.arrayContaining(['m','m²','m³','kos']));
 });
 it('vrsta dela je obvezna in ponuja samo aktivne',async()=>{
  await open();await pick('Nova postavka');const d=await dialog();const select=d.getByLabelText('Vrsta dela') as HTMLSelectElement;
  expect(select.required).toBe(true);const names=within(select).getAllByRole('option').map(o=>o.textContent);
  expect(names).toContain('Keramika');expect(names).toContain('Beljenje');expect(names).not.toContain('Staro delo');
  await fill(d,'Naziv','Nova');await userEvent.click(d.getByRole('button',{name:'Shrani postavko'}));expect(writes()).toHaveLength(0);
 });
 it('izbira vrste dela prekopira delo v polja, ki ostanejo urejljiva, in pošlje urejene vrednosti',async()=>{
  await open();await pick('Nova postavka');const d=await dialog();
  await fill(d,'Naziv','Polaganje keramike');await fill(d,'Opis','Priprava podlage');await userEvent.selectOptions(d.getByLabelText('Enota'),'m²');
  await userEvent.selectOptions(d.getByLabelText('Vrsta dela'),'v1');
  expect(Number((d.getByLabelText('Urna postavka (€)') as HTMLInputElement).value)).toBe(25);expect(Number((d.getByLabelText('Število ur') as HTMLInputElement).value)).toBe(8);expect(Number((d.getByLabelText('Število delavcev') as HTMLInputElement).value)).toBe(2);
  await fill(d,'Urna postavka (€)','30');await fill(d,'Cena na enoto','10');await fill(d,'Popust (%)','10');await fill(d,'Stopnja DDV (%)','22');
  await userEvent.click(d.getByRole('button',{name:'Shrani postavko'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P,'POST',{naziv:'Polaganje keramike',opis:'Priprava podlage',vrsta_dela_id:'v1',enota:'m2',cena_na_enoto:'10',kolicina:'1',popust:'0.1',stopnja_ddv:'0.22',urna_postavka:'30',stevilo_ur:expect.stringMatching(/^8(\.0+)?$/),stevilo_delavcev:2}));
 });
 it('delo brez dela (vrsta z 0 €) se prekopira kot ničle',async()=>{
  await open();await pick('Nova postavka');const d=await dialog();await userEvent.selectOptions(d.getByLabelText('Vrsta dela'),'v2');
  expect(Number((d.getByLabelText('Urna postavka (€)') as HTMLInputElement).value)).toBe(0);expect(Number((d.getByLabelText('Število ur') as HTMLInputElement).value)).toBe(0);
 });
 it('urejanje obstoječe postavke je izpolnjeno in shranjuje s PUT',async()=>{
  await open();await pick('Uredi Polaganje keramike');const d=await dialog();
  expect((d.getByLabelText('Naziv') as HTMLInputElement).value).toBe('Polaganje keramike');expect((d.getByLabelText('Vrsta dela') as HTMLSelectElement).value).toBe('v1');expect((d.getByLabelText('Enota') as HTMLSelectElement).value).toBe('m2');
  await userEvent.click(d.getByRole('button',{name:'Shrani postavko'}));
  await waitFor(()=>expect(mockedApi.mock.calls.some(c=>c[1]===P+'/i1'&&c[2]==='PUT')).toBe(true));
 });
 it('sprotni predogled izračuna: delo, neto, DDV in skupaj sledijo vnosu',async()=>{
  await open();await pick('Uredi Polaganje keramike');const d=await dialog();const g=d.getByRole('group',{name:'Predogled izračuna'});
  expect(g.textContent).toMatch(money('400,00'));expect(g.textContent).toMatch(money('540,00'));expect(g.textContent).toMatch(money('118,80'));expect(g.textContent).toMatch(money('658,80'));
  await fill(d,'Popust (%)','0');expect(d.getByRole('group',{name:'Predogled izračuna'}).textContent).toMatch(money('600,00'));expect(d.getByRole('group',{name:'Predogled izračuna'}).textContent).toMatch(money('732,00'));
  await fill(d,'Število delavcev','1');expect(d.getByRole('group',{name:'Predogled izračuna'}).textContent).toMatch(money('200,00'));expect(d.getByRole('group',{name:'Predogled izračuna'}).textContent).toMatch(money('400,00'));
 });
 it('napaka strežnika pri shranjevanju ostane v predalu kot opozorilo',async()=>{
  failure=new Error('Neaktivne vrste dela ni mogoče uporabiti.');await open();await pick('Nova postavka');const d=await dialog();
  await fill(d,'Naziv','X');await fill(d,'Opis','Y');await userEvent.selectOptions(d.getByLabelText('Vrsta dela'),'v2');await fill(d,'Cena na enoto','1');
  await userEvent.click(d.getByRole('button',{name:'Shrani postavko'}));expect((await screen.findByRole('alert')).textContent).toContain('Neaktivne vrste dela ni mogoče uporabiti.');expect(screen.getByRole('dialog')).toBeTruthy();
 });
 it('dodaj iz cenika pošlje količino in popust kot niz',async()=>{
  await open();await pick('Dodaj iz cenika');const d=await dialog();await userEvent.click(await d.findByRole('button',{name:'Izberi Rušenje estriha'}));
  await userEvent.type(d.getByLabelText('Količina'),'4');await userEvent.type(d.getByLabelText('Popust (%)'),'10');await userEvent.click(d.getByRole('button',{name:'Dodaj postavko'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/iz-cenika','POST',{postavka_cenika_id:'c1',kolicina:'4',popust:'0.1'}));
 });
});

describe('Postavke projekta: izmere',()=>{
 const panel=async(name:string)=>{await open();await pick('Izmere '+name);return dialog();};
 it('panel našteje izmere z znakom + ali − in prikaže skupaj izmer',async()=>{
  const d=await panel('Polaganje keramike');const items=d.getAllByRole('listitem');expect(items).toHaveLength(3);
  expect(items[0].textContent).toMatch(/\+\s?20\s?m²/);expect(items[0].textContent).toMatch(/5\s?×\s?4/);expect(items[1].textContent).toMatch(/\+\s?2\s?m²/);expect(items[2].textContent).toMatch(/−\s?2\s?m²/);
  expect(d.getByRole('group',{name:'Izračun izmere'}).textContent).toMatch(/Skupaj izmer[^]*20\s?m²/);
 });
 it('m² ima dolžino, višino, kosi in odštej, ne pa širine',async()=>{
  const d=await panel('Polaganje keramike');for(const l of ['Dolžina','Višina','Kosi'])expect(d.getByLabelText(l)).toBeTruthy();
  expect(d.queryByLabelText('Širina')).toBeNull();expect(d.getByRole('checkbox',{name:'Odštej'})).toBeTruthy();expect((d.getByLabelText('Kosi') as HTMLInputElement).value).toBe('1');
 });
 it('m ima samo dolžino in kosi',async()=>{
  const d=await panel('Polaganje roba');expect(d.getByLabelText('Dolžina')).toBeTruthy();expect(d.getByLabelText('Kosi')).toBeTruthy();for(const l of ['Višina','Širina'])expect(d.queryByLabelText(l)).toBeNull();
 });
 it('m³ ima dolžino, višino, širino in kosi',async()=>{
  const d=await panel('Zasip');for(const l of ['Dolžina','Višina','Širina','Kosi'])expect(d.getByLabelText(l)).toBeTruthy();
 });
 it('kos ima samo kosi',async()=>{
  const d=await panel('Montaža vrat');expect(d.getByLabelText('Kosi')).toBeTruthy();for(const l of ['Dolžina','Višina','Širina'])expect(d.queryByLabelText(l)).toBeNull();
 });
 it('sprotni izračun vrednosti izmere in skupne izmere, tudi z odštevanjem',async()=>{
  const d=await panel('Polaganje keramike');await fill(d,'Dolžina','3');await fill(d,'Višina','2');await fill(d,'Kosi','4');
  const g=()=>d.getByRole('group',{name:'Izračun izmere'}).textContent!;expect(g()).toMatch(/Vrednost izmere[^]*24\s?m²/);expect(g()).toMatch(/Skupaj izmer[^]*44\s?m²/);
  await userEvent.click(d.getByRole('checkbox',{name:'Odštej'}));await fill(d,'Kosi','1');await fill(d,'Dolžina','1');await fill(d,'Višina','1');expect(g()).toMatch(/Skupaj izmer[^]*19\s?m²/);
 });
 it('izmera, ki bi dala negativno količino, je zavrnjena že v obrazcu',async()=>{
  const d=await panel('Polaganje keramike');await userEvent.click(d.getByRole('checkbox',{name:'Odštej'}));await fill(d,'Dolžina','30');await fill(d,'Višina','1');
  expect(d.getByText('Izmere bi dale negativno količino.')).toBeTruthy();expect((d.getByRole('button',{name:'Dodaj izmero'}) as HTMLButtonElement).disabled).toBe(true);
 });
 it('doda izmero m² in pošlje samo polja te enote kot nize',async()=>{
  const d=await panel('Polaganje keramike');await fill(d,'Dolžina','3');await fill(d,'Višina','2');await fill(d,'Kosi','4');await userEvent.click(d.getByRole('button',{name:'Dodaj izmero'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i1/izmere','POST',{odstej:false,kosi:'4',dolzina:'3',visina:'2'}));
  await waitFor(()=>expect(mockedApi.mock.calls.filter(c=>c[1]===P&&!c[2]).length).toBeGreaterThan(1));
 });
 it('odštevalna izmera pošlje odstej true',async()=>{
  const d=await panel('Polaganje keramike');await userEvent.click(d.getByRole('checkbox',{name:'Odštej'}));await fill(d,'Dolžina','1');await fill(d,'Višina','1');await userEvent.click(d.getByRole('button',{name:'Dodaj izmero'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i1/izmere','POST',{odstej:true,kosi:'1',dolzina:'1',visina:'1'}));
 });
 it('izmera v m, m³ in kos pošlje samo polja svoje enote',async()=>{
  let d=await panel('Polaganje roba');await fill(d,'Dolžina','7');await userEvent.click(d.getByRole('button',{name:'Dodaj izmero'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i2/izmere','POST',{odstej:false,kosi:'1',dolzina:'7'}));
  await userEvent.click(screen.getByRole('button',{name:'Zapri'}));d=await (async()=>{await pick('Izmere Zasip');return dialog();})();
  await fill(d,'Dolžina','2');await fill(d,'Višina','3');await fill(d,'Širina','4');await userEvent.click(d.getByRole('button',{name:'Dodaj izmero'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i3/izmere','POST',{odstej:false,kosi:'1',dolzina:'2',visina:'3',sirina:'4'}));
  await userEvent.click(screen.getByRole('button',{name:'Zapri'}));d=await (async()=>{await pick('Izmere Montaža vrat');return dialog();})();
  await fill(d,'Kosi','3');await userEvent.click(d.getByRole('button',{name:'Dodaj izmero'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i4/izmere','POST',{odstej:false,kosi:'3'}));
 });
 it('odstrani izmero pošlje DELETE na izmero',async()=>{
  const d=await panel('Polaganje keramike');await userEvent.click(d.getByRole('button',{name:'Odstrani izmero 3'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/i1/izmere/z3','DELETE'));
 });
 it('strežniška napaka QFP25 se pokaže kot opozorilo',async()=>{
  failure=new Error('Izmere bi dale negativno količino.');const d=await panel('Polaganje keramike');await userEvent.click(d.getByRole('button',{name:'Odstrani izmero 1'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Izmere bi dale negativno količino.');
 });
});

describe('Postavke projekta v delovnem prostoru mojstra',()=>{
 const session={access_token:'t',user:{email:'ana@example.test'}} as Session;
 it('projekt ima gumb Postavke, ki odpre postavke tega projekta',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/me'?{id:'u',e_posta:'ana@example.test',ime:'Ana',priimek:'Novak',vloge:[{id:'r',podjetje_id:'a',vloga:'mojster',naziv:'A'}]}
   :path==='/podjetja'?[{id:'a',naziv:'A',aktivno:true}]:path==='/podjetja/a/projekti'?[{id:'p1',naziv:'Obnova kopalnice',opis:'x',lokacija_izvedbe:'Maribor',faza:'pregled',stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'j@example.test',termin_od:null,termin_do:null}]
   :path===P?data:path==='/podjetja/a/vrste-dela'?trades:[]);
  render(<WorkspacePage client={client} session={session}/>);
  await userEvent.click(await within(await screen.findByRole('navigation',{name:'Glavna navigacija'})).findByRole('button',{name:'Projekti'}));
  await pickMenu('Obnova kopalnice','Postavke');
  expect(await screen.findByText('Polaganje keramike')).toBeTruthy();expect(mockedApi).toHaveBeenCalledWith(client,P);
 });
});
