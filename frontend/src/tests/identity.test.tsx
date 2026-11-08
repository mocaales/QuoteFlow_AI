import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { render, expectToast } from './render';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import Login from '../features/identity/components/Login';
import Workspace from '../pages/WorkspacePage';
import Admin from '../features/administration/components/Admin';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);
const signIn = vi.fn(); const signUp = vi.fn(); const signOut = vi.fn();
const client = { auth: { signInWithPassword: signIn, signUp, signOut } } as unknown as SupabaseClient;
beforeEach(() => { vi.clearAllMocks(); });

async function fillLogin() {
 const user = userEvent.setup();
 await user.type(screen.getByLabelText('E-pošta'), 'user@example.test');
 await user.type(screen.getByLabelText('Geslo'), 'Local-test-123!');
 return user;
}

describe('US-01 prijava in registracija', () => {
 it('prikaže zavrnjeno prijavo brez odpiranja delovnega prostora', async () => {
  signIn.mockResolvedValue({ error: { code: 'invalid_credentials' }, data: {} });
  render(<Login client={client}/>);
  const user = await fillLogin(); await user.click(screen.getByRole('button', { name: 'Prijavi se' }));
  expect((await screen.findByRole('alert')).textContent).toContain('E-pošta ali geslo ni pravilno');
  expect(signIn).toHaveBeenCalledWith({ email: 'user@example.test', password: 'Local-test-123!' });
 });
 it('pri registraciji brez seje pojasni potrditev e-pošte', async () => {
  signUp.mockResolvedValue({ error: null, data: { session: null } });
  render(<Login client={client}/>);
  await userEvent.click(screen.getByRole('button', { name: /Nimate računa/ }));
  const user = await fillLogin(); await user.click(screen.getByRole('button', { name: 'Registriraj se' }));
  await expectToast('Preverite e-pošto');
  expect(signUp).toHaveBeenCalledOnce();
  expect((screen.getByLabelText('Geslo') as HTMLInputElement).value).toBe('');
 });
 it('uporabniku brez poslovnih vlog ne pokaže administracije ali podatkov podjetij', async () => {
  mockedApi.mockImplementation(async (_client, path) => path === '/me' ? { id: 'u', e_posta: 'user@example.test', vloge: [] } : []);
  const session = { access_token: 'token', user: { email: 'user@example.test' } } as Session;
  render(<Workspace client={client} session={session}/>);
  expect(await screen.findByText('Dostop še ni dodeljen')).toBeTruthy();
  expect(screen.queryByText('Dodaj podjetje')).toBeNull();
 });
});

describe('US-02 administracija', () => {
 it('odvzem vloge prikaže šele po uspešnem shranjevanju in osvežitvi podatkov', async () => {
  let active = true;
  mockedApi.mockImplementation(async (_client, path, method) => {
   if (path === '/podjetja') return [{ id: 'c', naziv: 'Podjetje A', aktivno: true }];
   if (path === '/admin/uporabniki') return [{ id: 'u', e_posta: 'user@example.test' }];
   if (path === '/admin/vloge') return [{ id: 'r', uporabnik_id: 'u', e_posta: 'user@example.test', podjetje_id: 'c', naziv: 'Podjetje A', vloga: 'delavec', aktivna: active }];
   if (path === '/admin/vloge/r' && method === 'PATCH') { active = false; return {}; }
   return {};
  });
  render(<Admin client={client}/>);
  // Preoblikovana administracija (master-detail): izberi podjetje, odvzem zahteva potrditev, odvzeta vloga je privzeto skrita.
  await userEvent.click(await screen.findByRole('button', { name: /^Podjetje A/ }));
  await userEvent.click(await screen.findByRole('button', { name: 'Odvzemi vlogo Delavec uporabniku user@example.test' }));
  expect(mockedApi.mock.calls.some(c => c[2] === 'PATCH')).toBe(false);
  await userEvent.click(screen.getByRole('button', { name: 'Odvzemi vlogo' }));
  await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(client, '/admin/vloge/r', 'PATCH', { aktivna: false }));
  await waitFor(() => expect(screen.queryByText('user@example.test')).toBeNull());
  await userEvent.selectOptions(screen.getByLabelText('Stanje'), 'Odvzete');
  expect(await screen.findByRole('button', { name: /Ponovno aktiviraj.*user@example\.test/ })).toBeTruthy();
 });
 it('ne prikaže lažnega uspeha, če shranjevanje podjetja ni dovoljeno', async () => {
  mockedApi.mockImplementation(async (_client, path, method) => {
   if (method === 'POST') throw new Error('Za to dejanje nimate pravice.');
   return path === '/admin/uporabniki' ? [{id:'u',e_posta:'u@example.test',ime:'Ana',priimek:'Novak'}] : [];
  });
  render(<Admin client={client}/>);
  await waitFor(() => expect(screen.queryByText('Nalagam podatke …')).toBeNull());
  await userEvent.click(screen.getByRole('tab', { name: 'Podjetja' }));
  await userEvent.click(screen.getByRole('button', { name: 'Dodaj podjetje' }));
  const dialog = within(await screen.findByRole('dialog'));
  await userEvent.type(dialog.getByLabelText('Naziv podjetja'), 'Novo podjetje');
  await userEvent.selectOptions(dialog.getByLabelText('Lastnik podjetja'),'u');
  await userEvent.type(dialog.getByLabelText('Matična številka'),'1234567');
  await userEvent.type(dialog.getByLabelText('Naslov podjetja'),'Naslov 1');
  await userEvent.click(dialog.getByRole('button', { name: 'Dodaj podjetje' }));
  expect((await screen.findByRole('alert')).textContent).toContain('nimate pravice');
  expect(screen.queryByText('Podjetje je shranjeno.')).toBeNull();
 });
});
