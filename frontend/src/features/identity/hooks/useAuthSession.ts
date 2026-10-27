import { useEffect, useState } from 'react';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import { createAuthClient } from '../../../lib/supabase';

export function useAuthSession() {
 const [client, setClient] = useState<SupabaseClient | null>(null);
 const [session, setSession] = useState<Session | null>(null);
 const [loaded, setLoaded] = useState(false);
 const [error, setError] = useState('');
 useEffect(() => {
  let mounted = true; let unsubscribe: (() => void) | undefined;
  createAuthClient().then(c => {
   if (!mounted) return;
   setClient(c);
   const { data } = c.auth.onAuthStateChange((_event, s) => { if (mounted) { setSession(s); setLoaded(true); } });
   unsubscribe = () => data.subscription.unsubscribe();
   c.auth.getSession().then(({ data, error }) => { if (mounted) { setSession(data.session); setLoaded(true); if (error) setError('Prijavne seje ni mogoče obnoviti.'); } });
  }).catch(e => { if (mounted) { setError(e.message); setLoaded(true); } });
  return () => { mounted = false; unsubscribe?.(); };
 }, []);
 return { client, session, loaded, error };
}
