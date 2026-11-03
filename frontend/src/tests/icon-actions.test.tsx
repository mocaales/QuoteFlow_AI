import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import Admin from '../features/administration/components/Admin';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';
import type { CatalogItem } from '../features/supplier/types';

// Row actions are icon-only: a full accessible name for assistive tech, a short visible tooltip.
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);
const client = { auth: { signOut: vi.fn() } } as unknown as SupabaseClient;
const item: CatalogItem = { id:'i', podjetje_id:'a', vrsta:'blago', opis:'Ležaj 6205', enota:'kos', cena_na_enoto:'12.45', strosek_na_enoto:'8', dobavni_rok_dni:5, aktivna:true, potrjeno_ob:null, razpolozljiva_kolicina:'4', zaloga_potrjeno_ob:null };
beforeEach(() => { vi.clearAllMocks(); });

function iconOnly(button: HTMLElement, tip: string) {
 expect(button.textContent?.trim()).toBe('');
 expect(button.querySelector('svg')).toBeTruthy();
 expect(button.getAttribute('data-tip')).toBe(tip);
}

describe('Dejanja z ikonami', () => {
 it('cenik ureja in potrjuje postavke z ikonama svinčnika in kljukice', async () => {
  mockedApi.mockImplementation(async (_c, path) => path.endsWith('/cenik') ? [item] : []);
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  iconOnly(await screen.findByRole('button', { name: 'Uredi Ležaj 6205' }), 'Uredi');
  iconOnly(screen.getByRole('button', { name: 'Potrdi' }), 'Potrdi');
  await userEvent.click(screen.getByRole('button', { name: 'Uredi Ležaj 6205' }));
  expect(screen.getByRole('dialog')).toBeTruthy();
 });

 it('zaloga se ureja z ikono, gumbi obrazca imajo ikono in besedilo', async () => {
  mockedApi.mockImplementation(async (_c, path) => path.endsWith('/cenik') ? [item] : []);
  render(<SupplierWorkspace client={client} companyId="a" tab="zaloge"/>);
  const edit = await screen.findByRole('button', { name: 'Zaloga za Ležaj 6205' });
  iconOnly(edit, 'Uredi zalogo');
  await userEvent.click(edit);
  for (const name of ['Potrdi zalogo', 'Prenehaj voditi zalogo']) expect(screen.getByRole('button', { name }).querySelector('svg')).toBeTruthy();
 });

 it('ponovni poskus po napaki je ikona', async () => {
  mockedApi.mockRejectedValue(new Error('Podatkovna baza trenutno ni na voljo.'));
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  iconOnly(await screen.findByRole('button', { name: 'Poskusi znova' }), 'Poskusi znova');
 });

 it('administracija ureja podjetja in vloge z ikonami', async () => {
  mockedApi.mockImplementation(async (_c, path) => path === '/podjetja' ? [{ id:'a', naziv:'A', stanje:'aktivno' }]
   : path === '/admin/uporabniki' ? [{ id:'u', e_posta:'u@example.test' }]
   : path === '/admin/vloge' ? [{ id:'r', uporabnik_id:'u', e_posta:'u@example.test', podjetje_id:'a', naziv:'A', vloga:'ponudnik', aktivna:true },
     { id:'s', uporabnik_id:'u', e_posta:'u@example.test', podjetje_id:'a', naziv:'A', vloga:'nabavnik', aktivna:false }] : []);
  render(<Admin client={client}/>);
  const edit = await screen.findByRole('button', { name: 'Uredi A' });
  iconOnly(edit, 'Uredi');
  iconOnly(screen.getByRole('button', { name: 'Odvzemi' }), 'Odvzemi vlogo');
  iconOnly(screen.getByRole('button', { name: 'Aktiviraj' }), 'Ponovno aktiviraj');
  await userEvent.click(edit);
  expect((screen.getByLabelText('Naziv podjetja') as HTMLInputElement).value).toBe('A');
  for (const name of ['Shrani spremembe', 'Prekliči', 'Dodeli vlogo']) expect(screen.getByRole('button', { name }).querySelector('svg')).toBeTruthy();
 });

 it('izbira podjetja na pregledu je ikona', async () => {
  mockedApi.mockImplementation(async (_c, path) => path === '/me' ? { id:'u', e_posta:'u@example.test', vloge:[{ id:'r', podjetje_id:'a', vloga:'ponudnik', naziv:'A' }, { id:'s', podjetje_id:'b', vloga:'nabavnik', naziv:'B' }] }
   : path === '/podjetja' ? [{ id:'a', naziv:'A', stanje:'aktivno' }, { id:'b', naziv:'B', stanje:'aktivno' }] : []);
  render(<WorkspacePage client={client} session={{ access_token:'t', user:{ email:'u@example.test' } } as Session}/>);
  await waitFor(() => expect(screen.queryByText('Preverjam dostop …')).toBeNull());
  iconOnly(screen.getByRole('button', { name: 'Izberi B' }), 'Izberi');
 });
});
