import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import { api, ApiError } from '../services/api';

vi.mock('../services/api', async importOriginal => ({
 ...await importOriginal<typeof import('../services/api')>(), api: vi.fn(),
}));
const mockedApi = vi.mocked(api);
const client = {} as SupabaseClient;
const session = { access_token: 'token', user: { email: 'admin@example.test' } } as Session;
let admin = true;
let failure: Error | null;
let release: (() => void) | undefined;
let wait: Promise<void> | undefined;

beforeEach(() => {
 vi.clearAllMocks(); admin = true; failure = null; wait = undefined; release = undefined;
 mockedApi.mockImplementation(async (_client, path) => {
  if (path === '/me') {
   if (wait) await wait;
   if (failure) throw failure;
   return { id: 'u', e_posta: 'admin@example.test', vloge: admin ? [{ id: 'r', podjetje_id: null, vloga: 'administrator', naziv: null }] : [] };
  }
  return [];
 });
});
// Navigation and the overview both offer the same action; target navigation explicitly.
async function editCompany() {
 render(<WorkspacePage client={client} session={session}/>);
 await waitFor(() => expect(screen.queryByText('Preverjam dostop …')).toBeNull());
 await userEvent.click(within(screen.getByRole('navigation', { name: 'Glavna navigacija' })).getByRole('button', { name: 'Podjetja in pravice' }));
 await screen.findByLabelText('Naziv podjetja');
 await userEvent.type(screen.getByLabelText('Naziv podjetja'), 'Neshranjen naziv');
}

describe('Osveževanje pravic v ozadju', () => {
 it('ohrani isti obrazec in vnos med čakanjem ter po vrnitvi fokusa', async () => {
  await editCompany();
  const input = screen.getByLabelText('Naziv podjetja');
  wait = new Promise<void>(resolve => { release = resolve; });
  await act(async () => { window.dispatchEvent(new Event('focus')); });
  expect(screen.getByLabelText('Naziv podjetja')).toBe(input);
  expect((input as HTMLInputElement).value).toBe('Neshranjen naziv');
  expect(screen.queryByText('Preverjam dostop …')).toBeNull();
  expect((screen.getByRole('button', { name: 'Osveži pravice' }) as HTMLButtonElement).disabled).toBe(false);
  await act(async () => { release!(); });
  expect(screen.getByLabelText('Naziv podjetja')).toBe(input);
  expect((input as HTMLInputElement).value).toBe('Neshranjen naziv');
 });
 it('pri začasni omrežni napaki ohrani obrazec in omogoča ponovni poskus', async () => {
  await editCompany(); failure = new TypeError('Failed to fetch');
  await act(async () => { window.dispatchEvent(new Event('focus')); });
  expect((await screen.findByRole('alert')).textContent).toContain('Pravic trenutno ni mogoče osvežiti');
  expect((screen.getByLabelText('Naziv podjetja') as HTMLInputElement).value).toBe('Neshranjen naziv');
  failure = null;
  await userEvent.click(screen.getByRole('button', { name: 'Osveži pravice' }));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect((screen.getByLabelText('Naziv podjetja') as HTMLInputElement).value).toBe('Neshranjen naziv');
 });
 it('po dejanskem odvzemu administratorske vloge odstrani administratorski pogled', async () => {
  await editCompany(); admin = false;
  await act(async () => { window.dispatchEvent(new Event('focus')); });
  expect(await screen.findByText('Dostop še ni dodeljen')).toBeTruthy();
  expect(screen.queryByLabelText('Naziv podjetja')).toBeNull();
 });
 it.each([401,403])('pri odgovoru %s odstrani predhodno dovoljeni pogled', async status => {
  await editCompany(); failure = new ApiError('Dostop ni več dovoljen.', status);
  await act(async () => { window.dispatchEvent(new Event('focus')); });
  expect((await screen.findByRole('alert')).textContent).toContain('Dostop ni več dovoljen');
  expect(screen.queryByLabelText('Naziv podjetja')).toBeNull();
 });
});
