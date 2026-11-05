import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const item={id:'i',podjetje_id:'a',naziv:'Rušenje estriha',opis:'Odstranitev',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'12.45',stopnja_ddv:'.22',aktivna:true};
beforeEach(()=>{vi.clearAllMocks();mockedApi.mockImplementation(async (_c,path)=>path.endsWith('/cenik')?[item]:[]);});
describe('Cenik in materiali',()=>{
 it('shrani delo z decimalno ceno in pretvorbo odstotka DDV',async()=>{
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'Nova postavka'}));
  const form=within(screen.getByRole('dialog'));
  await user.type(form.getByLabelText('Naziv'),'Polaganje');await user.type(form.getByLabelText('Opis'),'Polaganje ploščic');
  await user.type(form.getByLabelText('Vrsta dela'),'Keramika');
  await user.clear(form.getByLabelText('Enota'));await user.type(form.getByLabelText('Enota'),'m2');
  await user.type(form.getByLabelText('Cena na enoto (€)'),'45.125');
  await user.clear(form.getByLabelText('DDV (%)'));await user.type(form.getByLabelText('DDV (%)'),'22');
  await user.click(form.getByRole('button',{name:'Shrani postavko'}));
  await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
  expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/cenik','POST',expect.objectContaining({naziv:'Polaganje',vrsta_dela:'Keramika',cena_na_enoto:'45.125',stopnja_ddv:'0.220000'}));
 });
 it('pri napaki ohrani obrazec in ne prikaže uspeha',async()=>{
  mockedApi.mockImplementation(async(_c,path,method)=>{if(method==='PUT')throw new Error('Pravica je odvzeta.');return path.endsWith('/cenik')?[item]:[];});
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Uredi Rušenje estriha'}));
  await userEvent.click(screen.getByRole('button',{name:'Shrani postavko'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Pravica je odvzeta');expect(screen.getByRole('dialog')).toBeTruthy();
 });
 it('zalogo vodi za material po lokaciji in ohrani ničelno količino',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path.endsWith('/materiali')?[{id:'m',vrsta_materiala_id:'k',sifra:'LEP1',naziv:'Lepilo',enota:'kg',cena_na_enoto:'2',aktiven:true}]:path.endsWith('/materiali/m/zaloga')?[{material_id:'m',lokacija:'Maribor',kolicina:'0'}]:path.endsWith('/vrste-materiala')?[{id:'k',podjetje_id:'a',naziv:'Lepila'}]:[]);
  render(<SupplierWorkspace client={client} companyId="a" tab="zaloge"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Zaloga za Lepilo: Maribor'}));
  const form=within(screen.getByRole('dialog'));
  expect((form.getByLabelText('Lokacija') as HTMLInputElement).value).toBe('Maribor');
  expect((form.getByLabelText('Količina (kg)') as HTMLInputElement).value).toBe('0');
  await userEvent.click(form.getByRole('button',{name:'Shrani zalogo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/materiali/m/zaloga','PUT',{lokacija:'Maribor',kolicina:'0'}));
 });
 it('ob menjavi podjetja ne prikaže cenika prejšnjega',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/me'?{id:'u',e_posta:'u@example.test',ime:'Ana',priimek:'Novak',vloge:[{podjetje_id:'a',vloga:'mojster'},{podjetje_id:'b',vloga:'mojster'}]}:path==='/podjetja'?[{id:'a',naziv:'A',aktivno:true},{id:'b',naziv:'B',aktivno:true}]:path==='/podjetja/a/cenik'?[item]:[]);
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'u@example.test'}} as Session}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Cenik'}));expect(await screen.findByText('Rušenje estriha')).toBeTruthy();
  await userEvent.selectOptions(screen.getByLabelText('Aktivno podjetje'),'b');expect(screen.queryByText('Rušenje estriha')).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Cenik'}));
  expect(await screen.findByText('Dodajte prvo postavko')).toBeTruthy();
 });
 it('ob vrnitvi v brskalnik ohrani isti panel in neshranjeno postavko',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/me'?{id:'u',e_posta:'u@example.test',ime:'Ana',priimek:'Novak',vloge:[{podjetje_id:'a',vloga:'mojster'}]}:path==='/podjetja'?[{id:'a',naziv:'A',aktivno:true}]:[]);
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'u@example.test'}} as Session}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Cenik'}));await userEvent.click(await screen.findByRole('button',{name:'Nova postavka'}));
  const dialog=screen.getByRole('dialog');await userEvent.type(within(dialog).getByLabelText('Naziv'),'Neshranjeno delo');
  await act(async()=>{window.dispatchEvent(new Event('focus'));});
  expect(screen.getByRole('dialog')).toBe(dialog);expect((within(dialog).getByLabelText('Naziv') as HTMLInputElement).value).toBe('Neshranjeno delo');
 });
});
