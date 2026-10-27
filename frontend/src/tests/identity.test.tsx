import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
  expect((await screen.findByRole('status')).textContent).toContain('Preverite e-pošto');
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
   if (path === '/podjetja') return [{ id: 'c', naziv: 'Podjetje A', stanje: 'aktivno' }];
   if (path === '/admin/uporabniki') return [{ id: 'u', e_posta: 'user@example.test' }];
   if (path === '/admin/vloge') return [{ id: 'r', uporabnik_id: 'u', e_posta: 'user@example.test', podjetje_id: 'c', naziv: 'Podjetje A', vloga: 'nabavnik', aktivna: active }];
   if (path === '/admin/vloge/r' && method === 'PATCH') { active = false; return {}; }
   return {};
  });
  render(<Admin client={client}/>);
  await userEvent.click(await screen.findByRole('button', { name: 'Odvzemi' }));
  expect(await screen.findByRole('button', { name: 'Aktiviraj' })).toBeTruthy();
  expect(mockedApi).toHaveBeenCalledWith(client, '/admin/vloge/r', 'PATCH', { aktivna: false });
 });
 it('ne prikaže lažnega uspeha, če shranjevanje podjetja ni dovoljeno', async () => {
  mockedApi.mockImplementation(async (_client, path, method) => {
   if (method === 'POST') throw new Error('Za to dejanje nimate pravice.');
   return [];
  });
  render(<Admin client={client}/>);
  await waitFor(() => expect(screen.queryByText('Nalagam podatke …')).toBeNull());
  await userEvent.type(screen.getByLabelText('Naziv podjetja'), 'Novo podjetje');
  await userEvent.click(screen.getByRole('button', { name: 'Dodaj podjetje' }));
  expect((await screen.findByRole('alert')).textContent).toContain('nimate pravice');
  expect(screen.queryByText('Podjetje je shranjeno.')).toBeNull();
 });
});
