import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import App from '../app/App';
import { createAuthClient } from '../lib/supabase';
import { api } from '../services/api';

vi.mock('../lib/supabase', () => ({ createAuthClient: vi.fn() }));
vi.mock('../services/api', () => ({ api: vi.fn() }));

const session = { access_token: 'token', user: { email: 'user@example.test' } } as Session;
let onChange: (event: string, session: Session | null) => void;
const unsubscribe = vi.fn();
const client = {
 auth: {
  getSession: vi.fn(async () => ({ data: { session }, error: null })),
  onAuthStateChange: vi.fn(callback => {
   onChange = callback;
   return { data: { subscription: { unsubscribe } } };
  }),
 },
} as unknown as SupabaseClient;

beforeEach(() => {
 vi.clearAllMocks();
 vi.mocked(createAuthClient).mockResolvedValue(client);
 vi.mocked(api).mockImplementation(async (_client, path) => path === '/me' ? { id: 'u', e_posta: 'user@example.test', vloge: [] } : []);
});

describe('Življenjski cikel prijavne seje', () => {
 it('obnovi sejo, se odzove na odjavo in odstrani naročnino ob zaprtju', async () => {
  const view = render(<App/>);
  expect(await screen.findByText('Dostop še ni dodeljen')).toBeTruthy();
  await act(async () => { onChange('SIGNED_OUT', null); });
  expect(await screen.findByRole('heading', { name: 'Prijava' })).toBeTruthy();
  expect(screen.queryByText('Dostop še ni dodeljen')).toBeNull();
  view.unmount();
  expect(unsubscribe).toHaveBeenCalledOnce();
 });

 it('ob nedosegljivi konfiguraciji prikaže napako brez delovnega prostora', async () => {
  vi.mocked(createAuthClient).mockRejectedValue(new Error('Prijava ni nastavljena.'));
  render(<App/>);
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Prijava ni nastavljena.'));
  expect(screen.queryByText('Moja podjetja')).toBeNull();
  expect(api).not.toHaveBeenCalled();
 });
});
