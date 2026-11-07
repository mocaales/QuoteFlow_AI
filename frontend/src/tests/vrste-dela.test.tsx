import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
// Model v3: materiali niso več pri postavki cenika, ampak pri vrsti dela (zavihek »Vrste dela« delovnega prostora dobavitelja).
const mat=(id:string,sifra:string,naziv:string,aktiven=true)=>({id,vrsta_materiala_id:'k',sifra,naziv,enota:'kg',cena_na_enoto:'2',aktiven});
const line={material_id:'m1',sifra:'LEP-1',naziv:'Lepilo za ploščice',enota:'kg',aktiven:true,kolicina_na_enoto:'4.5000',cena_na_enoto:'2.0000'};
const trade=(id:string,naziv:string,more={})=>({id,naziv,opis:'',urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,aktivna:true,cena_dela:'400.00',materiali:[line],...more});
let trades:unknown[];let failure:Error|null;
const V='/podjetja/a/vrste-dela';
beforeEach(()=>{vi.clearAllMocks();trades=[trade('v1','Keramika'),trade('v2','Rušenje',{urna_postavka:'0.0000',stevilo_ur:'0.0000',stevilo_delavcev:1,cena_dela:'0.00',materiali:[]})];failure=null;
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(!method){if(path===V)return trades;if(path==='/podjetja/a/materiali')return [mat('m1','LEP-1','Lepilo za ploščice'),mat('m2','CEM-1','Cement'),mat('m3','STA-1','Stari fugirnik',false)];return [];}
  if(failure)throw failure;return {};
 });
});
const open=()=>render(<SupplierWorkspace client={client} companyId="a" tab="vrste-dela"/>);
const materials=async(name:string)=>{open();await userEvent.click(await screen.findByRole('button',{name:'Materiali '+name}));return within(await screen.findByRole('dialog'));};
describe('Vrste dela',()=>{
 it('seznam pokaže vrsto dela, izpeljano ceno dela in število delavcev, delo brez dela z 0,00 €',async()=>{
  open();const row=await screen.findByRole('row',{name:/Keramika/});
  expect(row.textContent).toMatch(/400,00\s?€/);expect(row.textContent).toMatch(/2 delavca|2 delavc/);expect(screen.getByRole('row',{name:/Rušenje/}).textContent).toMatch(/0,00\s?€/);
  expect(mockedApi).toHaveBeenCalledWith(client,V);
 });
 it('nova vrsta dela pošlje nize in celo število delavcev; delo brez dela (0 €) je veljavno',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Nova vrsta dela'}));const d=within(await screen.findByRole('dialog'));
  for(const [label,value] of [['Naziv','Beljenje'],['Opis','Dve plasti'],['Urna postavka (€)','0'],['Število ur','0']]){const el=d.getByLabelText(label);await userEvent.clear(el);await userEvent.type(el,value);}
  await userEvent.click(d.getByRole('button',{name:'Shrani vrsto dela'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,V,'POST',{naziv:'Beljenje',opis:'Dve plasti',urna_postavka:'0',stevilo_ur:'0',stevilo_delavcev:1,aktivna:true}));
 });
 it('urejanje je izpolnjeno in shranjuje s PUT; števila delavcev ni mogoče spustiti pod 1',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Uredi Keramika'}));const d=within(await screen.findByRole('dialog'));
  expect((d.getByLabelText('Naziv') as HTMLInputElement).value).toBe('Keramika');expect(Number((d.getByLabelText('Število delavcev') as HTMLInputElement).value)).toBe(2);expect((d.getByLabelText('Število delavcev') as HTMLInputElement).min).toBe('1');
  await userEvent.click(d.getByRole('button',{name:'Shrani vrsto dela'}));await waitFor(()=>expect(mockedApi.mock.calls.some(c=>c[1]===V+'/v1'&&c[2]==='PUT')).toBe(true));
 });
 it('napaka pri shranjevanju ostane v predalu kot opozorilo',async()=>{
  failure=new Error('Podjetje ima lahko največ 500 vrst dela.');open();await userEvent.click(await screen.findByRole('button',{name:'Nova vrsta dela'}));const d=within(await screen.findByRole('dialog'));
  await userEvent.type(d.getByLabelText('Naziv'),'X');await userEvent.click(d.getByRole('button',{name:'Shrani vrsto dela'}));
  expect((await screen.findByRole('alert')).textContent).toContain('500 vrst dela');expect(screen.getByRole('dialog')).toBeTruthy();
 });
 it('napaka pri nalaganju pokaže opozorilo brez praznega stanja',async()=>{
  mockedApi.mockRejectedValue(new Error('Podatkovna baza trenutno ni na voljo.'));open();
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText('Dodajte prvo vrsto dela')).toBeNull();
 });
});
describe('Materiali vrste dela',()=>{
 it('količino prikaže z vejico brez končnih ničel',async()=>{
  trades=[trade('v1','Keramika',{materiali:[{...line,kolicina_na_enoto:'3.0000'},{...line,material_id:'m2',naziv:'Cement',kolicina_na_enoto:'0.0250'}]})];
  const p=await materials('Keramika');expect(await p.findByText('Lepilo za ploščice · 3 kg na enoto')).toBeTruthy();expect(p.getByText('Cement · 0,025 kg na enoto')).toBeTruthy();
 });
 it('brez materialov pokaže prazno stanje, material ni obvezen',async()=>{
  const p=await materials('Rušenje');expect(await p.findByText('Brez materialov')).toBeTruthy();
 });
 it('dodaj material pošlje količino kot niz in ponuja samo aktivne materiale',async()=>{
  const p=await materials('Keramika');await p.findByText('Lepilo za ploščice · 4,5 kg na enoto');
  const select=p.getByLabelText('Material');const options=within(select).getAllByRole('option').map(o=>o.textContent??'');
  expect(options.some(o=>o.includes('Cement'))).toBe(true);expect(options.some(o=>o.includes('Stari fugirnik'))).toBe(false);
  await userEvent.selectOptions(select,'m2');await userEvent.type(p.getByLabelText('Količina na enoto'),'1.25');await userEvent.click(p.getByRole('button',{name:'Dodaj material'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,V+'/v1/materiali/m2','PUT',{kolicina_na_enoto:'1.25'}));
 });
 it('spremeni količino obstoječe vrstice z nizom',async()=>{
  const p=await materials('Keramika');const q=await p.findByLabelText(/Količina.*Lepilo za ploščice/);
  await userEvent.clear(q);await userEvent.type(q,'5.25');await userEvent.tab();
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,V+'/v1/materiali/m1','PUT',{kolicina_na_enoto:'5.25'}));
 });
 it('odstrani material iz vrste dela',async()=>{
  const p=await materials('Keramika');await userEvent.click(await p.findByRole('button',{name:'Odstrani Lepilo za ploščice'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,V+'/v1/materiali/m1','DELETE'));
 });
 it('pri 409 pokaže napako o neaktivnem materialu',async()=>{
  failure=new Error('Neaktivnega materiala ni mogoče dodati v sestavo.');
  const p=await materials('Keramika');await p.findByText('Lepilo za ploščice · 4,5 kg na enoto');
  await userEvent.selectOptions(p.getByLabelText('Material'),'m2');await userEvent.type(p.getByLabelText('Količina na enoto'),'1');await userEvent.click(p.getByRole('button',{name:'Dodaj material'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Neaktivnega materiala ni mogoče dodati v sestavo.');
 });
 it('v ceniku ni več gumba Materialna sestava',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/podjetja/a/cenik'?[{id:'i',podjetje_id:'a',naziv:'Polaganje keramike',opis:'x',vrsta_dela_id:'v1',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'35',stopnja_ddv:'.22',aktivna:true}]:[]);
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);await screen.findByText('Polaganje keramike');
  expect(screen.queryByRole('button',{name:/Materialna sestava/})).toBeNull();
 });
});
