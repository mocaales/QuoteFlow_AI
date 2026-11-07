import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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
const item: CatalogItem = {id:'i',podjetje_id:'a',naziv:'Rušení estriha',opis:'Odstranitev',vrsta_dela_id:'v2',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'12.45',stopnja_ddv:'.22',aktivna:true};
beforeEach(() => { vi.clearAllMocks(); });

function iconOnly(button: HTMLElement, tip: string) {
 expect(button.textContent?.trim()).toBe('');
 expect(button.querySelector('svg')).toBeTruthy();
 expect(button.getAttribute('data-tip')).toBe(tip);
}

describe('Dejanja z ikonami', () => {
 it('cenik ureja postavke z dostopno ikono', async () => {
  mockedApi.mockImplementation(async (_c, path) => path.endsWith('/cenik') ? [item] : []);
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  iconOnly(await screen.findByRole('button', { name: 'Uredi Rušení estriha' }), 'Uredi');
  await userEvent.click(screen.getByRole('button', { name: 'Uredi Rušení estriha' }));
  expect(screen.getByRole('dialog')).toBeTruthy();
 });

 it('ponovni poskus po napaki je ikona', async () => {
  mockedApi.mockRejectedValue(new Error('Podatkovna baza trenutno ni na voljo.'));
  render(<SupplierWorkspace client={client} companyId="a" tab="cenik"/>);
  iconOnly(await screen.findByRole('button', { name: 'Poskusi znova' }), 'Poskusi znova');
 });

 it('administracija ureja podjetja in vloge z ikonami', async () => {
  mockedApi.mockImplementation(async (_c, path) => path === '/podjetja' ? [{ id:'a', naziv:'A', aktivno:true }]
   : path === '/admin/uporabniki' ? [{ id:'u', e_posta:'u@example.test' }]
   : path === '/admin/vloge' ? [{ id:'r', uporabnik_id:'u', e_posta:'u@example.test', podjetje_id:'a', naziv:'A', vloga:'mojster', aktivna:true },
     { id:'s', uporabnik_id:'u', e_posta:'u@example.test', podjetje_id:'a', naziv:'A', vloga:'delavec', aktivna:false }] : []);
  render(<Admin client={client}/>);
  // Preoblikovano: urejanje podjetja ostane ikona, dejanja vlog so besedilni gumbi z ikono (ne samo ikona).
  await userEvent.click(await screen.findByRole('tab', { name: 'Podjetja' }));
  const edit = await screen.findByRole('button', { name: 'Uredi A' });
  iconOnly(edit, 'Uredi');
  await userEvent.click(edit);
  const dialog = within(await screen.findByRole('dialog'));
  expect((dialog.getByLabelText('Naziv podjetja') as HTMLInputElement).value).toBe('A');
  expect(dialog.getByRole('button', { name: 'Shrani spremembe' }).querySelector('svg')).toBeTruthy();
  await userEvent.click(dialog.getByRole('button', { name: 'Zapri' }));
  await userEvent.click(screen.getByRole('tab', { name: 'Po podjetjih' }));
  await userEvent.click(await screen.findByRole('button', { name: /^A/ }));
  const revoke = await screen.findByRole('button', { name: /Odvzemi.*u@example\.test/ });
  expect(revoke.textContent).toMatch(/Odvzemi/); expect(revoke.querySelector('svg')).toBeTruthy(); expect(revoke.getAttribute('data-tip')).toBeNull();
  await userEvent.selectOptions(screen.getByLabelText('Stanje'), 'Odvzete');
  const restore = await screen.findByRole('button', { name: /Ponovno aktiviraj/ });
  expect(restore.textContent).toMatch(/Ponovno aktiviraj/); expect(restore.querySelector('svg')).toBeTruthy();
 });

 it('izbira podjetja na pregledu je ikona', async () => {
  mockedApi.mockImplementation(async (_c, path) => path === '/me' ? { id:'u', e_posta:'u@example.test', vloge:[{ id:'r', podjetje_id:'a', vloga:'mojster', naziv:'A' }, { id:'s', podjetje_id:'b', vloga:'mojster', naziv:'B' }] }
   : path === '/podjetja' ? [{ id:'a', naziv:'A', aktivno:true }, { id:'b', naziv:'B', aktivno:true }] : []);
  render(<WorkspacePage client={client} session={{ access_token:'t', user:{ email:'u@example.test' } } as Session}/>);
  await waitFor(() => expect(screen.queryByText('Preverjam dostop …')).toBeNull());
  iconOnly(screen.getByRole('button', { name: 'Izberi B' }), 'Izberi');
 });
});
