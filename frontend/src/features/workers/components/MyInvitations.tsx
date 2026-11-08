import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Icon from '../../../components/Icon';
import { ApiError } from '../../../services/api';
import { answerInvitation, getMyInvitations } from '../api';
import type { MyInvitation } from '../types';
import { useToast } from '../../../lib/toast';

export default function MyInvitations({ client, onAccepted }: { client: SupabaseClient; onAccepted: () => void }) {
 const [items, setItems] = useState<MyInvitation[]>([]);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const toast = useToast();
 const [confirming, setConfirming] = useState<string | null>(null);
 const seq = useRef(0), pending = useRef(false);
 const load = useCallback(async () => { const id = ++seq.current, rows = await getMyInvitations(client); if (id === seq.current) setItems(rows); }, [client]);
 // A failed load stays silent: the card is optional and the rest of Pregled works without it.
 useEffect(() => { load().catch(() => undefined); return () => { seq.current++; }; }, [load]);
 async function answer(i: MyInvitation, accept: boolean) {
  if (pending.current) return;
  pending.current = true; setBusy(true); setError(''); setConfirming(null);
  try {
   await answerInvitation(client, i.id, accept); toast(accept ? `Povabilo podjetja ${i.podjetje_naziv} je sprejeto.` : 'Povabilo je zavrnjeno.');
   await load().catch(() => undefined); if (accept) onAccepted();
  } catch (e) { setError(e instanceof ApiError && [401, 403, 409, 404].includes(e.status) ? e.message : 'Povabila ni mogoče obdelati. Poskusite znova.'); await load().catch(() => undefined); }
  finally { pending.current = false; setBusy(false); }
 }
 if (!items.length && !error) return null;
 return <section className="panel invitations" aria-labelledby="povabila-v-podjetja"><h2 id="povabila-v-podjetja">Povabila v podjetja</h2>
  {error && <p role="alert" className="alert">{error}</p>}
  <ul className="invitation-list">{items.map(i => <li key={i.id}>
   <p><strong>{i.podjetje_naziv}</strong> vas vabi kot delavca · povabil {i.povabil}</p>
   {confirming === i.id ? <div className="row-confirm"><p>{`Zavrnem povabilo podjetja ${i.podjetje_naziv}?`}</p><button type="button" className="secondary small" disabled={busy} onClick={() => void answer(i, false)}><Icon name="close"/>Zavrni povabilo</button><button type="button" className="secondary small" onClick={() => setConfirming(null)}>Prekliči</button></div>
    : <div className="button-row"><button type="button" disabled={busy} aria-label={`Sprejmi povabilo podjetja ${i.podjetje_naziv}`} onClick={() => void answer(i, true)}><Icon name="check"/>Sprejmi</button><button type="button" className="secondary" disabled={busy} aria-label={`Zavrni povabilo podjetja ${i.podjetje_naziv}`} onClick={() => setConfirming(i.id)}><Icon name="close"/>Zavrni</button></div>}
  </li>)}</ul></section>;
}
