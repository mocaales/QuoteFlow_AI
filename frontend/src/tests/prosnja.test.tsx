import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import Admin from '../features/administration/components/Admin';
import MasterApplication from '../features/identity/components/MasterApplication';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);
const client = {} as SupabaseClient;
const row = (change = {}) => ({ id: 'p1', uporabnik_id: 'u', naziv_podjetja: 'Mojster Novak d.o.o.', maticna_stevilka: '1234567000', davcna_stevilka: null, naslov_podjetja: 'Cesta 1, Maribor', stanje: 'oddana', podjetje_id: null, oddano_ob: '2026-11-01T10:00:00Z', odloceno_ob: null, ...change });
let mine: unknown[];
let pending: unknown[];
let failure: Error | null;
const calls = (path: string) => mockedApi.mock.calls.filter(c => c[1] === path);
beforeEach(() => {
 vi.clearAllMocks(); mine = []; pending = []; failure = null;
 mockedApi.mockImplementation(async (_c, path, method) => {
  if (path === '/me') return { id: 'u', e_posta: 'ana@example.test', ime: 'Ana', priimek: 'Novak', vloge: [{ id: 'r', podjetje_id: null, vloga: 'stranka', naziv: null }] };
  if (path === '/prosnje' && method === 'POST') { if (failure) throw failure; mine = [row()]; return row(); }
  if (path === '/prosnje') return mine;
  if (path === '/admin/prosnje') return pending;
  if (path.startsWith('/admin/prosnje/') && method === 'POST') { pending = pending.map(p => ({ ...(p as object), stanje: 'odobrena' })); return row({ stanje: 'odobrena' }); }
  return [];
 });
});
describe('Prošnja mojstra', () => {
 it('stranka v navigaciji vidi prošnjo za mojstra in odpre obrazec', async () => {
  render(<WorkspacePage client={client} session={{ access_token: 'token', user: { email: 'ana@example.test' } } as Session}/>);
  const nav = await screen.findByRole('navigation', { name: 'Glavna navigacija' });
  await userEvent.click(await within(nav).findByRole('button', { name: 'Prošnja za mojstra' }));
  expect(await screen.findByRole('button', { name: 'Oddaj prošnjo' })).toBeTruthy();
 });
 it('brez prošenj pokaže obrazec z označenimi polji, obvezna polja so required', async () => {
  render(<MasterApplication client={client}/>);
  for (const label of ['Naziv podjetja', 'Matična številka', 'Naslov podjetja']) expect((await screen.findByLabelText(label) as HTMLInputElement).required).toBe(true);
  expect((screen.getByLabelText('Davčna številka (neobvezno)') as HTMLInputElement).required).toBe(false);
 });
 it('oddaja pošlje prirezane podatke na /prosnje in pokaže stanje Oddana brez obrazca', async () => {
  render(<MasterApplication client={client}/>);
  await userEvent.type(await screen.findByLabelText('Naziv podjetja'), '  Mojster Novak d.o.o. ');
  await userEvent.type(screen.getByLabelText('Matična številka'), '1234567000');
  await userEvent.type(screen.getByLabelText('Naslov podjetja'), 'Cesta 1, Maribor');
  await userEvent.click(screen.getByRole('button', { name: 'Oddaj prošnjo' }));
  await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(client, '/prosnje', 'POST', { naziv_podjetja: 'Mojster Novak d.o.o.', maticna_stevilka: '1234567000', davcna_stevilka: null, naslov_podjetja: 'Cesta 1, Maribor' }));
  expect(await screen.findByText('Oddana')).toBeTruthy();
  expect(screen.getByText('Mojster Novak d.o.o.')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Oddaj prošnjo' })).toBeNull();
 });
 it('izpolnjena davčna številka se pošlje', async () => {
  render(<MasterApplication client={client}/>);
  await userEvent.type(await screen.findByLabelText('Naziv podjetja'), 'A'); await userEvent.type(screen.getByLabelText('Matična številka'), '1'); await userEvent.type(screen.getByLabelText('Naslov podjetja'), 'B');
  await userEvent.type(screen.getByLabelText('Davčna številka (neobvezno)'), 'SI12345678');
  await userEvent.click(screen.getByRole('button', { name: 'Oddaj prošnjo' }));
  await waitFor(() => expect(calls('/prosnje').find(c => c[2] === 'POST')?.[3]).toMatchObject({ davcna_stevilka: 'SI12345678' }));
 });
 it('prazna obvezna polja ne sprožijo oddaje', async () => {
  render(<MasterApplication client={client}/>);
  await userEvent.click(await screen.findByRole('button', { name: 'Oddaj prošnjo' }));
  expect(calls('/prosnje').filter(c => c[2] === 'POST')).toHaveLength(0);
 });
 it('napaka API-ja je prikazana in obrazec ostane', async () => {
  failure = new Error('Podjetje ali oddana prošnja s to matično številko že obstaja.');
  render(<MasterApplication client={client}/>);
  await userEvent.type(await screen.findByLabelText('Naziv podjetja'), 'A'); await userEvent.type(screen.getByLabelText('Matična številka'), '1'); await userEvent.type(screen.getByLabelText('Naslov podjetja'), 'B');
  await userEvent.click(screen.getByRole('button', { name: 'Oddaj prošnjo' }));
  expect((await screen.findByRole('alert')).textContent).toContain('s to matično številko že obstaja');
  expect(screen.getByRole('button', { name: 'Oddaj prošnjo' })).toBeTruthy();
 });
 it('ob oddani prošnji obrazca ni, zavrnjena in odobrena pa imata oznako stanja', async () => {
  mine = [row(), row({ id: 'p2', naziv_podjetja: 'Stara d.o.o.', stanje: 'zavrnjena' }), row({ id: 'p3', naziv_podjetja: 'Stari mojster', stanje: 'odobrena' })];
  render(<MasterApplication client={client}/>);
  expect(await screen.findByText('Oddana')).toBeTruthy(); expect(screen.getByText('Zavrnjena')).toBeTruthy(); expect(screen.getByText('Odobrena')).toBeTruthy();
  expect(screen.queryByLabelText('Naziv podjetja')).toBeNull();
 });
 it('po zavrnitvi lahko stranka odda novo prošnjo', async () => {
  mine = [row({ stanje: 'zavrnjena' })];
  render(<MasterApplication client={client}/>);
  expect(await screen.findByRole('button', { name: 'Oddaj prošnjo' })).toBeTruthy();
 });
});
describe('Admin: prošnje mojstrov', () => {
 const entry = (change = {}) => row({ e_posta: 'marko@example.test', ime: 'Marko', priimek: 'Kos', ...change });
 it('admin vidi razdelek z e-pošto vlagatelja in gumbi samo pri oddanih prošnjah', async () => {
  pending = [entry(), entry({ id: 'p2', naziv_podjetja: 'Gradnje Kos d.o.o.', stanje: 'zavrnjena' })];
  render(<Admin client={client}/>);
  expect(await screen.findByRole('heading', { name: 'Prošnje mojstrov' })).toBeTruthy();
  expect((await screen.findAllByText('marko@example.test')).length).toBeGreaterThan(0);
  expect(screen.getByRole('button', { name: 'Odobri Mojster Novak d.o.o.' })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Zavrni Mojster Novak d.o.o.' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Odobri Gradnje Kos d.o.o.' })).toBeNull();
 });
 it('odobritev pošlje odlocitev in osveži seznam', async () => {
  pending = [entry()];
  render(<Admin client={client}/>);
  await userEvent.click(await screen.findByRole('button', { name: 'Odobri Mojster Novak d.o.o.' }));
  await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(client, '/admin/prosnje/p1/odlocitev', 'POST', { odobri: true }));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Odobri Mojster Novak d.o.o.' })).toBeNull());
  expect(calls('/admin/prosnje').length).toBeGreaterThan(1);
 });
 it('zavrnitev pošlje odobri false', async () => {
  pending = [entry()];
  render(<Admin client={client}/>);
  await userEvent.click(await screen.findByRole('button', { name: 'Zavrni Mojster Novak d.o.o.' }));
  await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(client, '/admin/prosnje/p1/odlocitev', 'POST', { odobri: false }));
 });
});
