import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';

vi.mock('../services/api', async importOriginal => ({
 ...await importOriginal<typeof import('../services/api')>(), api: vi.fn(),
}));
const mockedApi = vi.mocked(api);
const client = {} as SupabaseClient;
const session = { access_token: 'token', user: { email: 'nina@example.test' } } as Session;
beforeEach(() => {
 vi.clearAllMocks();
 mockedApi.mockImplementation(async (_client, path) => path === '/me'
  ? { id: 'u', e_posta: 'nina@example.test', vloge: [{ id: 'r', podjetje_id: 'a', vloga: 'ponudnik', naziv: 'Ležajna tehnika d.o.o.' }] }
  : path === '/podjetja' ? [{ id: 'a', naziv: 'Ležajna tehnika d.o.o.', stanje: 'aktivno' }] : []);
});

describe('Okvir delovnega prostora', () => {
 it('meni na telefonu odpre navigacijo in se po izbiri zapre', async () => {
  render(<WorkspacePage client={client} session={session}/>);
  await waitFor(() => expect(screen.queryByText('Preverjam dostop …')).toBeNull());
  const menu = screen.getByRole('button', { name: 'Meni' });
  expect(menu.getAttribute('aria-expanded')).toBe('false');
  expect(menu.getAttribute('aria-controls')).toBe(screen.getByRole('navigation', { name: 'Glavna navigacija' }).closest('[id]')!.id);
  await userEvent.click(menu);
  expect(menu.getAttribute('aria-expanded')).toBe('true');
  await userEvent.click(within(screen.getByRole('navigation', { name: 'Glavna navigacija' })).getByRole('button', { name: 'Cenik' }));
  expect(menu.getAttribute('aria-expanded')).toBe('false');
  expect(await screen.findByRole('heading', { level: 1, name: 'Cenik' })).toBeTruthy();
 });

 it('ime podjetja in prijavljeni račun sta vidna v okvirju', async () => {
  render(<WorkspacePage client={client} session={session}/>);
  await waitFor(() => expect(screen.queryByText('Preverjam dostop …')).toBeNull());
  expect(screen.getByLabelText('Aktivno podjetje')).toBeTruthy();
  expect(screen.getByText('nina@example.test')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Odjava' })).toBeTruthy();
 });
});
