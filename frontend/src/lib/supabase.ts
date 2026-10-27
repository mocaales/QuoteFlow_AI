import { createClient, type SupabaseClient } from '@supabase/supabase-js';

let clientPromise: Promise<SupabaseClient> | undefined;
export function createAuthClient(): Promise<SupabaseClient> {
 if (!clientPromise) clientPromise = loadAuthClient().catch(error => { clientPromise = undefined; throw error; });
 return clientPromise;
}
async function loadAuthClient(): Promise<SupabaseClient> {
 const response = await fetch('/api/config');
 if (!response.ok) throw new Error('Prijava ni nastavljena ali storitev ni dosegljiva.');
 const config = await response.json();
 return createClient(config.supabase_url, config.supabase_publishable_key, {
  auth: { storage: window.sessionStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
 });
}
