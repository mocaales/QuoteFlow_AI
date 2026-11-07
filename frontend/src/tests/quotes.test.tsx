import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import QuoteEditor from '../features/quotes/components/QuoteEditor';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const P='/podjetja/a/projekti/1/ponudbe';
const catalog=[
 {id:'i1',podjetje_id:'a',naziv:'Polaganje keramike',opis:'Priprava podlage',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'35.0000',stopnja_ddv:'0.22',aktivna:true},
 {id:'i3',podjetje_id:'a',naziv:'Zaključno čiščenje',opis:'Čiščenje',vrsta_dela:'Čiščenje',enota:'ura',cena_na_enoto:'20.0000',stopnja_ddv:'0.095',aktivna:false},
];
const line=(id:string,more={})=>({id,postavka_cenika_id:null,zaporedje:1,naziv:'Rušenje estriha',opis:'Odvoz',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'100.0000',kolicina:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60',materiali:[],...more});
const summary={id:'q1',stevilka:'P-2026-001',razlicica:1,stanje:'osnutek',poslano_ob:null,odgovorjeno_ob:null,velja_do:null,nadomescena:false,neto:'180.00',ddv:'39.60',skupaj:'219.60'};
const full=(more={})=>({...summary,postavke:[line('l1')],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'180.00',ddv:'39.60'}],...more});
let list:unknown[];let detail:unknown;let failure:Error|null;
beforeEach(()=>{vi.clearAllMocks();failure=null;list=[summary];detail=full();
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(path==='/podjetja/a/cenik')return catalog;
  if(path===P&&!method)return list;
  if(path===P+'/q1'&&!method)return detail;
  if(method){if(failure)throw failure;return path===P?full({postavke:[],neto:'0.00',ddv:'0.00',skupaj:'0.00'}):{};}
  return [];
 });
});
const open=()=>render(<QuoteEditor client={client} companyId="a" projectId="1"/>);
describe('Osnutek ponudbe',()=>{
 it('brez ponudbe ponudi ustvaritev osnutka in pošlje POST',async()=>{
  list=[];open();await userEvent.click(await screen.findByRole('button',{name:'Ustvari osnutek ponudbe'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P,'POST',{}));
 });
 it('pokaže številko, različico, postavke in vsote v evrih',async()=>{
  open();expect(await screen.findByRole('heading',{name:/P-2026-001/})).toBeTruthy();expect(screen.getByText(/različica 1/i)).toBeTruthy();
  expect(screen.getByText('Rušenje estriha')).toBeTruthy();
  const totals=screen.getByRole('group',{name:'Vsote ponudbe'});
  expect(totals.textContent).toMatch(/180,00\s?€/);expect(totals.textContent).toMatch(/39,60\s?€/);expect(totals.textContent).toMatch(/219,60\s?€/);
 });
 // Model v3: postavke in izmere se urejajo na projektu (project-items.test.tsx); osnutek ponudbe je glava s predogledom, zato so prejšnji testi urejanja vrstic ponudbe (dodaj iz cenika, ročni vnos, odstrani, zaklenjena ponudba) zastareli.
 it('osnutek je predogled: postavke se ne urejajo v ponudbi',async()=>{
  open();await screen.findByText('Rušenje estriha');
  for(const name of ['Dodaj iz cenika','Ročni vnos','Odstrani Rušenje estriha','Uredi Rušenje estriha'])expect(screen.queryByRole('button',{name})).toBeNull();
  expect(screen.getByRole('button',{name:'Pošlji stranki'})).toBeTruthy();
 });
 it('predogled pokaže skupno izmero postavke',async()=>{
  detail=full({postavke:[line('l1',{izmera_skupaj:'20.0000'})]});open();await screen.findByText('Rušenje estriha');
  expect(screen.getByRole('row',{name:/Rušenje estriha/}).textContent).toMatch(/20\s?m²/);
 });
 it('postavke ponudbe se nikoli ne pošiljajo na strežnik iz urejevalnika ponudbe',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi pošiljanje'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/q1/poslji','POST'));expect(mockedApi.mock.calls.some(c=>String(c[1]).includes('/postavke')&&!!c[2])).toBe(false);
 });
 it('pošlji stranki je onemogočen brez postavk in omogočen z njimi',async()=>{
  detail=full({postavke:[],neto:'0.00',ddv:'0.00',skupaj:'0.00'});const view=open();
  expect(((await screen.findByRole('button',{name:'Pošlji stranki'})) as HTMLButtonElement).disabled).toBe(true);view.unmount();
  detail=full();open();await screen.findByText('Rušenje estriha');expect((screen.getByRole('button',{name:'Pošlji stranki'}) as HTMLButtonElement).disabled).toBe(false);
 });
 it('poslana ponudba je samo za branje in ponuja novo različico',async()=>{
  list=[{...summary,stanje:'poslana',poslano_ob:'2026-11-06T09:00:00Z'}];detail=full({stanje:'poslana',poslano_ob:'2026-11-06T09:00:00Z'});
  open();await screen.findByText('Rušenje estriha');
  for(const name of ['Dodaj iz cenika','Ročni vnos','Odstrani Rušenje estriha','Uredi Rušenje estriha','Pošlji stranki'])expect(screen.queryByRole('button',{name})).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Pripravi novo različico'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P,'POST',{}));
 });
 it('napaka pri nalaganju ne pokaže praznega stanja',async()=>{
  mockedApi.mockRejectedValue(new Error('Podatkovna baza trenutno ni na voljo.'));open();
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByRole('button',{name:'Ustvari osnutek ponudbe'})).toBeNull();
 });
 it('pošlji stranki pošlje POST na poslji brez telesa in osveži ponudbo',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi pošiljanje'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,P+'/q1/poslji','POST'));
  await waitFor(()=>expect(mockedApi.mock.calls.filter(c=>c[1]===P+'/q1'&&!c[2]).length).toBeGreaterThan(1));
 });
 it('napaka pri pošiljanju se pokaže kot opozorilo in ponudba ostane osnutek',async()=>{
  failure=new Error('Veljavnost ponudbe je potekla.');
  open();await userEvent.click(await screen.findByRole('button',{name:'Pošlji stranki'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi pošiljanje'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Veljavnost ponudbe je potekla.');expect(screen.getByRole('button',{name:'Pošlji stranki'})).toBeTruthy();
 });
});
