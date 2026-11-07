import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import QuoteEditor from '../features/quotes/components/QuoteEditor';
import ProjectsWorkspace from '../features/projects/components/ProjectsWorkspace';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const P='/podjetja/a/projekti/1/ponudbe';
const line=(id:string,more={})=>({id,postavka_cenika_id:null,zaporedje:1,naziv:'Rušenje estriha',opis:'Odvoz',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'100.0000',kolicina:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60',materiali:[],...more});
const summary={id:'q1',stevilka:'P-2026-001',razlicica:1,stanje:'osnutek',poslano_ob:null,odgovorjeno_ob:null,velja_do:'2026-12-01',nadomescena:false,neto:'180.00',ddv:'39.60',skupaj:'219.60'};
const full=(more={})=>({...summary,postavke:[line('l1')],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'180.00',ddv:'39.60'}],...more});
let list:unknown[];let details:Record<string,unknown>;
beforeEach(()=>{vi.clearAllMocks();list=[summary];details={q1:full()};
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(path==='/podjetja/a/cenik')return [];
  if(path===P&&!method)return list;
  const m=path.match(/^\/podjetja\/a\/projekti\/1\/ponudbe\/(q\d)$/);if(m&&!method)return details[m[1]];
  if(method)return {};
  return [];
 });
});
const open=()=>render(<QuoteEditor client={client} companyId="a" projectId="1"/>);
const writes=()=>mockedApi.mock.calls.filter(c=>c[2]);
// Model v3: vrstice se urejajo kot postavke projekta (project-items.test.tsx); ponudba je predogled in pošiljanje.
describe('Ponudba ne ureja vrstic',()=>{
 it('osnutek, poslana in sprejeta ponudba nimajo gumbov za urejanje vrstic in ne pošljejo zapisov na postavke',async()=>{
  for(const stanje of ['osnutek','poslana','sprejeta']){
   list=[{...summary,stanje}];details={q1:full({stanje})};const view=open();await screen.findByText('Rušenje estriha');
   for(const name of ['Uredi Rušenje estriha','Odstrani Rušenje estriha','Dodaj iz cenika','Ročni vnos'])expect(screen.queryByRole('button',{name})).toBeNull();
   view.unmount();
  }
  expect(writes().length).toBe(0);
 });
});
describe('Potrditev pošiljanja ponudbe',()=>{
 it('klik na Pošlji stranki najprej zahteva potrditev in ne pošlje ničesar',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));
  expect(await screen.findByRole('button',{name:'Potrdi pošiljanje'})).toBeTruthy();expect(screen.getByRole('button',{name:'Prekliči'})).toBeTruthy();
  expect(writes().length).toBe(0);
 });
 it('Potrdi pošiljanje pošlje POST na poslji natanko enkrat',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi pošiljanje'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/q1/poslji','POST'));expect(writes().length).toBe(1);
 });
 it('Prekliči zapre potrditev brez zahtevka in pusti osnutek',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await userEvent.click(await screen.findByRole('button',{name:'Prekliči'}));
  expect(screen.queryByRole('button',{name:'Potrdi pošiljanje'})).toBeNull();expect(screen.getByRole('button',{name:'Pošlji stranki'})).toBeTruthy();expect(writes().length).toBe(0);
 });
 it('Escape zapre potrditev brez zahtevka',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await screen.findByRole('button',{name:'Potrdi pošiljanje'});await userEvent.keyboard('{Escape}');
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Potrdi pošiljanje'})).toBeNull());expect(writes().length).toBe(0);
 });
 it('potrditev pojasni, da poslane ponudbe ni več mogoče urejati',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));const confirm=await screen.findByRole('button',{name:'Potrdi pošiljanje'});
  const region=confirm.closest('[role="dialog"],[role="alertdialog"],section,form,div')!;expect(region.textContent).toMatch(/ne bo(ste)? (več )?mogoče (več )?(urejati|spreminjati)|zaklen|nespremenljiv/i);
 });
});
describe('Ponudba mojstra v poznejših fazah je samo za branje',()=>{
 const accepted=(more={})=>full({stanje:'sprejeta',poslano_ob:'2026-11-06T09:00:00Z',odgovorjeno_ob:'2026-11-07T09:00:00Z',...more});
 it('sprejeta ponudba nima nobenega gumba za urejanje, pošiljanje ali novo različico',async()=>{
  list=[{...summary,stanje:'sprejeta'}];details={q1:accepted()};open();expect(await screen.findByRole('heading',{name:/P-2026-001/})).toBeTruthy();
  for(const name of ['Dodaj iz cenika','Ročni vnos','Uredi Rušenje estriha','Odstrani Rušenje estriha','Pošlji stranki','Pripravi novo različico'])expect(screen.queryByRole('button',{name})).toBeNull();
  expect(screen.getByRole('group',{name:'Vsote ponudbe'}).textContent).toMatch(/219,60\s?€/);
 });
 it('ko je v1 sprejeta, urejevalnik pokaže sprejeto različico in ne osnutka v2',async()=>{
  list=[{...summary,stanje:'sprejeta'},{...summary,id:'q2',razlicica:2,stanje:'osnutek'}];details={q1:accepted(),q2:full({id:'q2',razlicica:2})};open();
  expect(await screen.findByText(/različica 1/i)).toBeTruthy();expect(screen.queryByText(/različica 2/i)).toBeNull();expect(screen.queryByRole('button',{name:'Pošlji stranki'})).toBeNull();expect(screen.queryByRole('button',{name:'Uredi Rušenje estriha'})).toBeNull();
 });
});
describe('Gumb Ponudba v delovnem prostoru',()=>{
 const project=(id:string,naziv:string,faza:string)=>({id,naziv,opis:'O',lokacija_izvedbe:'Maribor',faza,stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'janez@example.test',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null});
 const all=['termin','izvedba','obracun','zakljucen'].map((f,i)=>project(`p${i}`,`Projekt ${f}`,f));
 beforeEach(()=>{mockedApi.mockImplementation(async(_c,path)=>path==='/podjetja/a/projekti'?all:[]);});
 it.each(['termin','izvedba','obracun','zakljucen'])('v fazi %s je gumb Ponudba in odpre ponudbo',async faza=>{
  render(<ProjectsWorkspace client={client} companyId="a" renderQuote={p=><p>Ponudba projekta {p.naziv}</p>}/>);
  await userEvent.click(await screen.findByRole('button',{name:`Ponudba Projekt ${faza}`}));expect(await screen.findByText(`Ponudba projekta Projekt ${faza}`)).toBeTruthy();expect(screen.getByRole('button',{name:'Nazaj na projekte'})).toBeTruthy();
 });
});
