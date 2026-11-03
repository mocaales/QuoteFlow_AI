import type { SupabaseClient } from '@supabase/supabase-js';

export class ApiError extends Error {
 constructor(message: string, public readonly status: number) {
  super(message);
  this.name = 'ApiError';
 }
}

export async function api<T>(client: SupabaseClient, path: string, method = 'GET', body?: unknown): Promise<T> {
 const { data: { session } } = await client.auth.getSession();
 if (!session) throw new ApiError('Prijavite se ponovno.', 401);
 const response = await fetch('/api' + path, {
  method, headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
 });
 if (!response.ok) {
  const error = await response.json().catch(() => ({}));
  throw new ApiError(typeof error.detail === 'string' ? error.detail : 'Preverite vnesene podatke.', response.status);
 }
 return response.json();
}
