import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const item={id:'i',podjetje_id:'a',naziv:'Polaganje keramike',opis:'Polaganje',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'35',stopnja_ddv:'.22',aktivna:true};
const mat=(id:string,sifra:string,naziv:string,aktiven=true)=>({id,vrsta_materiala_id:'k',sifra,naziv,enota:'kg',cena_na_enoto:'2',aktiven});
const line={material_id:'m1',sifra:'LEP-1',naziv:'Lepilo za ploščice',enota:'kg',aktiven:true,kolicina_na_enoto:'4.5000'};
let lines:unknown[];let failure:Error|null;
const S='/podjetja/a/cenik/i/sestava';
beforeEach(()=>{vi.clearAllMocks();lines=[line];failure=null;
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(path===S&&!method)return lines;
  if(path.startsWith(S+'/')){if(failure)throw failure;return {};}
  if(path==='/podjetja/a/cenik')return [item];
  if(path==='/podjetja/a/materiali')return [mat('m1','LEP-1','Lepilo za ploščice'),mat('m2','CEM-1','Cement'),mat('m3','STA-1','Stari fugirnik',false)];
  return [];
 });
});
async function open(){render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
 await userEvent.click(await screen.findByRole('button',{name:/Materialna sestava.*Polaganje keramike/}));return within(await screen.findByRole('dialog'));}
describe('Materialna sestava',()=>{
 it('količino prikaže z vejico brez končnih ničel',async()=>{lines=[{...line,kolicina_na_enoto:'3.0000'},{...line,material_id:'m2',naziv:'Cement',kolicina_na_enoto:'0.0250'}];
  const p=await open();expect(await p.findByText('Lepilo za ploščice · 3 kg na m2')).toBeTruthy();expect(p.getByText('Cement · 0,025 kg na m2')).toBeTruthy();});
 it('odpre panel in pokaže vrstice z enotama materiala in postavke',async()=>{
  const p=await open();expect(await p.findByText('Lepilo za ploščice · 4,5 kg na m2')).toBeTruthy();
  expect(mockedApi).toHaveBeenCalledWith(client,S);
 });
 it('brez sestave pokaže prazno stanje',async()=>{
  lines=[];const p=await open();expect(await p.findByText('Brez materialne sestave')).toBeTruthy();
 });
 it('dodaj v sestavo pošlje količino kot niz in ponuja samo aktivne materiale',async()=>{
  const p=await open();await p.findByText('Lepilo za ploščice · 4,5 kg na m2');
  const select=p.getByLabelText('Material');const options=within(select).getAllByRole('option').map(o=>o.textContent??'');
  expect(options.some(o=>o.includes('Cement'))).toBe(true);expect(options.some(o=>o.includes('Stari fugirnik'))).toBe(false);
  await userEvent.selectOptions(select,'m2');await userEvent.type(p.getByLabelText('Količina na enoto'),'1.25');
  await userEvent.click(p.getByRole('button',{name:'Dodaj v sestavo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,S+'/m2','PUT',{kolicina_na_enoto:'1.25'}));
 });
 it('spremeni količino obstoječe vrstice z nizom',async()=>{
  const p=await open();const q=await p.findByLabelText(/Količina.*Lepilo za ploščice/);
  await userEvent.clear(q);await userEvent.type(q,'5.25');await userEvent.tab();
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,S+'/m1','PUT',{kolicina_na_enoto:'5.25'}));
 });
 it('odstrani vrstico iz sestave',async()=>{
  const p=await open();await userEvent.click(await p.findByRole('button',{name:'Odstrani Lepilo za ploščice'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,S+'/m1','DELETE'));
 });
 it('pri 409 pokaže napako o neaktivnem materialu',async()=>{
  failure=new Error('Neaktivnega materiala ni mogoče dodati v sestavo.');
  const p=await open();await p.findByText('Lepilo za ploščice · 4,5 kg na m2');
  await userEvent.selectOptions(p.getByLabelText('Material'),'m2');await userEvent.type(p.getByLabelText('Količina na enoto'),'1');
  await userEvent.click(p.getByRole('button',{name:'Dodaj v sestavo'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Neaktivnega materiala ni mogoče dodati v sestavo.');
 });
});
