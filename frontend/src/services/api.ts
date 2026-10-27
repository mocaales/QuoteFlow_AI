import type { SupabaseClient } from '@supabase/supabase-js';

export async function api<T>(client: SupabaseClient, path: string, method = 'GET', body?: unknown): Promise<T> {
 const { data: { session } } = await client.auth.getSession();
 if (!session) throw new Error('Prijavite se ponovno.');
 const response = await fetch('/api' + path, {
  method, headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
 });
 if (!response.ok) {
  const error = await response.json().catch(() => ({}));
  throw new Error(typeof error.detail === 'string' ? error.detail : 'Preverite vnesene podatke.');
 }
 return response.json();
}
