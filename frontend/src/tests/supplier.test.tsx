import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';
import type { CatalogItem } from '../features/supplier/types';

vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);
const client = { auth: { signOut: vi.fn() } } as unknown as SupabaseClient;
const item: CatalogItem = { id:'i', podjetje_id:'a', vrsta:'blago', opis:'Ležaj 6205', enota:'kos', cena_na_enoto:'12.4500', strosek_na_enoto:'8', dobavni_rok_dni:5, aktivna:true, potrjeno_ob:null, razpolozljiva_kolicina:null, zaloga_potrjeno_ob:null };
let items: CatalogItem[];
beforeEach(() => {
 vi.clearAllMocks();items=[{...item}];
 mockedApi.mockImplementation(async (_client, path) => path.endsWith('/cenik') ? items : []);
});

describe('Podatki ponudnika', () => {
 it('potrditev prikaže šele po uspešnem zapisu in ponovnem branju', async () => {
  mockedApi.mockImplementation(async (_client,path,method) => {
   if (path.endsWith('/potrditev')) { items=[{...item,potrjeno_ob:'2026-10-29T10:00:00Z'}];return items[0]; }
   return path.endsWith('/cenik') ? items : [];
  });
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Potrdi'}));
  expect(await screen.findByText('Potrjena')).toBeTruthy();
  expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/cenik/i/potrditev','POST');
 });
 it('shrani postavko z decimalnimi vrednostmi in brez izmišljene zaloge', async () => {
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  const user=userEvent.setup();
  await user.click(await screen.findByRole('button',{name:'Nova postavka'}));
  const dialog=screen.getByRole('dialog');
  await user.type(within(dialog).getByLabelText('Opis'),'Servis ležajev');
  await user.selectOptions(within(dialog).getByLabelText('Vrsta'),'storitev');
  await user.type(within(dialog).getByLabelText('Cena na enoto (€)'),'45.125');
  await user.type(within(dialog).getByLabelText('Strošek na enoto (€)'),'20');
  await user.click(within(dialog).getByRole('button',{name:'Shrani postavko'}));
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/cenik','POST',expect.objectContaining({vrsta:'storitev',cena_na_enoto:'45.125',strosek_na_enoto:'20',dobavni_rok_dni:null}));
 });
 it('pri napaki ohrani obrazec in ne prikaže uspeha', async () => {
  mockedApi.mockImplementation(async (_client,path,method) => { if(method==='PUT')throw new Error('Pravica je odvzeta.');return path.endsWith('/cenik')?items:[]; });
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Uredi Ležaj 6205'}));
  await userEvent.click(screen.getByRole('button',{name:'Shrani postavko'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Pravica je odvzeta');
  expect(screen.getByRole('dialog')).toBeTruthy();
  expect(screen.queryByText(/Postavka je shranjena/)).toBeNull();
 });
 it('loči neznano in ničelno zalogo ter ne pokaže storitev v zalogah', async () => {
  items=[item,{...item,id:'z',opis:'Prazen skladiščni artikel',razpolozljiva_kolicina:'0'}, {...item,id:'s',vrsta:'storitev',opis:'Montaža'}];
  render(<SupplierWorkspace client={client} companyId="a" tab="zaloge"/>);
  expect(await screen.findByText('Se ne vodi')).toBeTruthy();
  expect(screen.getByText('0 kos')).toBeTruthy();
  expect(screen.queryByText('Montaža')).toBeNull();
 });
 it('pretvori odstotke v natančne šestmestne deleže', async () => {
  render(<SupplierWorkspace client={client} companyId="a" tab="pravila"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Nova različica'}));
  const user=userEvent.setup();
  await user.type(screen.getByLabelText('Najmanjša marža (%)'),'20.1234');
  await user.type(screen.getByLabelText('Največji popust (%)'),'10');
  await user.type(screen.getByLabelText('Najdaljši dobavni rok (dni)'),'7');
  await user.click(screen.getByRole('button',{name:'Ustvari različico pravil'}));
  await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/pravila','POST',{najmanjsa_marza:'0.201234',najvecji_popust:'0.100000',najdaljsi_rok_dni:7,velja_od:null,velja_do:null}));
 });
 it('ob menjavi aktivnega podjetja ne prikaže podatkov prejšnjega', async () => {
  mockedApi.mockImplementation(async (_client,path) => {
   if(path==='/me')return {id:'u',e_posta:'test@example.test',vloge:[{podjetje_id:'a',vloga:'ponudnik'},{podjetje_id:'b',vloga:'ponudnik'}]};
   if(path==='/podjetja')return [{id:'a',naziv:'Podjetje A',stanje:'aktivno'},{id:'b',naziv:'Podjetje B',stanje:'aktivno'}];
   if(path==='/podjetja/a/cenik')return [item];
   return [];
  });
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'test@example.test'}} as Session}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Cenik'}));
  expect(await screen.findByText('Ležaj 6205')).toBeTruthy();
  await userEvent.selectOptions(screen.getByLabelText('Aktivno podjetje'),'b');
  expect(screen.queryByText('Ležaj 6205')).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Cenik'}));
  expect(await screen.findByText('Dodajte prvo postavko')).toBeTruthy();
  expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/b/cenik');
 });
 it('ob vrnitvi v brskalnik ohrani odprt panel in neshranjeno postavko', async () => {
  mockedApi.mockImplementation(async (_client,path) => {
   if(path==='/me')return {id:'u',e_posta:'test@example.test',vloge:[{podjetje_id:'a',vloga:'ponudnik'}]};
   if(path==='/podjetja')return [{id:'a',naziv:'Podjetje A',stanje:'aktivno'}];
   return [];
  });
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'test@example.test'}} as Session}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Cenik'}));
  await userEvent.click(await screen.findByRole('button',{name:'Nova postavka'}));
  const dialog=screen.getByRole('dialog');
  await userEvent.type(within(dialog).getByLabelText('Opis'),'Neshranjena postavka');
  await act(async () => { window.dispatchEvent(new Event('focus')); });
  expect(screen.getByRole('dialog')).toBe(dialog);
  expect((within(dialog).getByLabelText('Opis') as HTMLInputElement).value).toBe('Neshranjena postavka');
 });

});
