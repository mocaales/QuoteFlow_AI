import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import Admin from '../features/administration/components/Admin';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);
const client = {} as SupabaseClient;
const company = { id:'a', lastnik_id:'u', naziv:'Mojster A', maticna_stevilka:'1234567', davcna_stevilka:null, naslov:'Naslov 1', aktivno:true };
let role = 'admin';
beforeEach(() => {
 vi.clearAllMocks(); role = 'admin';
 mockedApi.mockImplementation(async (_client, path) => {
  if (path === '/me') return {id:'u',e_posta:'u@example.test',ime:'Ana',priimek:'Novak',vloge:[{id:'r',vloga:role,podjetje_id:role==='mojster'?'a':null,naziv:role==='mojster'?'Mojster A':null}]};
  if (path === '/podjetja') return [company];
  if (path === '/admin/uporabniki') return [{id:'u',e_posta:'u@example.test',ime:'Ana',priimek:'Novak'}];
  return [];
 });
});
describe('Novi relacijski model', () => {
 it('globalni admin vidi administracijo', async () => {
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'u@example.test'}} as Session}/>);
  expect(await within(screen.getByRole('navigation',{name:'Glavna navigacija'})).findByRole('button',{name:'Podjetja in pravice'})).toBeTruthy();
 });
 it('mojster ima cenik in zaloge brez starih prodajnih pravil', async () => {
  role='mojster';
  render(<WorkspacePage client={client} session={{access_token:'token',user:{email:'u@example.test'}} as Session}/>);
  const nav=await screen.findByRole('navigation',{name:'Glavna navigacija'});
  expect(await within(nav).findByRole('button',{name:'Cenik'})).toBeTruthy();
  expect(within(nav).getByRole('button',{name:'Zaloge'})).toBeTruthy();
  expect(within(nav).queryByRole('button',{name:'Prodajna pravila'})).toBeNull();
 });
 it('obrazec podjetja zahteva lastnika, matično številko in naslov', async () => {
  render(<Admin client={client}/>);
  // Preoblikovano: obrazec podjetja je v predalu zavihka Podjetja; vloga se dodeljuje v podjetju (Mojster ali Delavec, Stranka je globalna).
  await userEvent.click(await screen.findByRole('tab',{name:'Podjetja'}));
  await userEvent.click(screen.getByRole('button',{name:'Dodaj podjetje'}));
  const dialog=within(await screen.findByRole('dialog'));
  expect(dialog.getByLabelText('Lastnik podjetja')).toBeTruthy();
  expect(dialog.getByLabelText('Matična številka')).toBeTruthy();
  expect(dialog.getByLabelText('Naslov podjetja')).toBeTruthy();
  await userEvent.click(dialog.getByRole('button',{name:'Zapri'}));
  await userEvent.click(screen.getByRole('tab',{name:'Po podjetjih'}));
  await userEvent.click(await screen.findByRole('button',{name:/^Mojster A/}));
  await userEvent.click(await screen.findByRole('button',{name:'Dodaj člana'}));
  const roles=within(await screen.findByRole('dialog')).getAllByRole('radio').map(el=>el.closest('label')?.textContent?.trim().split(/\s/)[0]);
  expect(roles).toEqual(expect.arrayContaining(['Mojster','Delavec']));
  expect(roles).not.toContain('Stranka');expect(roles).not.toContain('Nabavnik');
 });
 it('cenik ponuja vsebino dela in DDV, ne internih stroškov in potrditve', async () => {
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  await userEvent.click(await screen.findByRole('button',{name:'Nova postavka'}));
  const dialog=screen.getByRole('dialog');
  expect(within(dialog).getByLabelText('Naziv')).toBeTruthy();
  expect(within(dialog).getByLabelText('Vrsta dela')).toBeTruthy();
  expect((within(dialog).getByLabelText('Opis') as HTMLTextAreaElement).required).toBe(true);
  expect(within(dialog).getByLabelText('DDV (%)')).toBeTruthy();
  expect(within(dialog).queryByLabelText('Strošek na enoto (€)')).toBeNull();
 });
});
