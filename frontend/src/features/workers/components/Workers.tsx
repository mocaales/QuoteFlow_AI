import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Icon from '../../../components/Icon';
import { ApiError } from '../../../services/api';
import { date, fold, plural } from '../../../utils/format';
import { cancelInvitation, getInvitations, getWorkers, inviteWorker, setWorkerActive } from '../api';
import type { Invitation, Worker } from '../types';

const generic = 'Povabila ni mogoče poslati. Preverite e-pošto in poskusite znova.';
const states: Record<string, [string, string]> = { povabljen: ['Čaka', 'pending'], sprejeto: ['Sprejeto', 'confirmed'], zavrnjeno: ['Zavrnjeno', 'inactive'], preklicano: ['Preklicano', 'inactive'], poteklo: ['Poteklo', 'inactive'] };
const fullName = (w: Worker) => [w.ime, w.priimek].filter(Boolean).join(' ') || w.e_posta;
export default function Workers({ client, companyId, companyName, userId }: { client: SupabaseClient; companyId: string; companyName: string; userId: string }) {
 const [items, setItems] = useState<Worker[]>([]);
 const [invites, setInvites] = useState<Invitation[]>([]);
 const [cancelling, setCancelling] = useState<string | null>(null);
 const [loaded, setLoaded] = useState(false);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [query, setQuery] = useState('');
 const [state, setState] = useState('aktivni');
 const [confirming, setConfirming] = useState<string | null>(null);
 const seq = useRef(0), pending = useRef(false);
 const load = useCallback(async () => { const id = ++seq.current, [rows, sent] = await Promise.all([getWorkers(client, companyId), getInvitations(client, companyId)]); if (id === seq.current) { setItems(rows); setInvites(sent); } }, [client, companyId]);
 const start = useCallback(() => { setError(''); setLoaded(false); load().then(() => setLoaded(true), e => setError(e instanceof Error ? e.message : 'Delavcev ni mogoče naložiti.')); }, [load]);
 useEffect(() => { start(); return () => { seq.current++; }; }, [start]);
 async function run(action: () => Promise<string>, fail: (e: unknown) => string) {
  if (pending.current) return false;
  pending.current = true; setBusy(true); setError(''); setNotice('');
  try { const message = await action(); await load(); setNotice(message); return true; }
  catch (e) { setError(fail(e)); return false; }
  finally { pending.current = false; setBusy(false); }
 }
 function add(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const form = e.currentTarget, email = String(new FormData(form).get('e_posta') ?? '').trim();
  // One fixed success text: the answer must never reveal whether the account exists.
  void run(async () => { await inviteWorker(client, companyId, { e_posta: email }); form.reset(); return 'Povabilo je poslano. Delavec ga mora sprejeti v svojem računu.'; },
   err => err instanceof ApiError && [401, 403, 429].includes(err.status) ? err.message : err instanceof ApiError && err.status === 422 ? 'Vnesite veljaven e-poštni naslov.' : generic);
 }
 const cancel = (i: Invitation) => { setCancelling(null); void run(async () => { await cancelInvitation(client, companyId, i.id); return 'Povabilo je preklicano.'; }, err => err instanceof Error ? err.message : 'Povabila ni mogoče preklicati.'); };
 const change = (w: Worker, active: boolean) => { setConfirming(null); void run(async () => { await setWorkerActive(client, companyId, w.id, active); return active ? 'Dostop delavca je ponovno omogočen.' : 'Dostop delavca je odvzet.'; }, err => err instanceof Error ? err.message : 'Spremembe ni mogoče shraniti.'); };
 const shown = items.filter(w => (state === 'vsi' || w.aktivna === (state === 'aktivni')) && (!query || fold(`${fullName(w)} ${w.e_posta}`).includes(fold(query))));
 return <>
  <div className="page-title"><div><h1>Delavci</h1><p>{`Sodelavci podjetja ${companyName}`}</p></div></div>
  {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
  <form className="inline-form" onSubmit={add}>
   <div className="field-stack"><label>E-pošta delavca<input name="e_posta" type="email" required minLength={3} maxLength={254} autoComplete="off" aria-describedby="delavec-pomoc"/></label>
    <p id="delavec-pomoc" className="muted">Delavec mora biti že registriran in imeti potrjeno e-pošto.</p></div>
   <button disabled={busy}><Icon name="user-plus"/>Povabi delavca</button>
  </form>
  {loaded && !!invites.length && <section className="membership-section" aria-labelledby="povabila-naslov"><h2 id="povabila-naslov">Povabila</h2><div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">Povabila delavcev</caption><thead><tr><th>E-pošta</th><th>Stanje</th><th className="num">Poslano</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
   {invites.map(i => { const [label, tone] = states[i.stanje] ?? [i.stanje, 'inactive']; return <tr key={i.id}><td><strong>{i.e_posta}</strong></td><td><span className={`status-badge ${tone}`}>{label}</span></td><td className="num" data-label="Poslano:">{date(i.poslano_ob)}</td>
    <td className="num">{i.stanje !== 'povabljen' ? null : cancelling === i.id ? <div className="row-confirm"><p>{`Prekličem povabilo za ${i.e_posta}?`}</p><button type="button" className="secondary small" disabled={busy} onClick={() => cancel(i)}><Icon name="close"/>Prekliči povabilo</button><button type="button" className="secondary small" onClick={() => setCancelling(null)}>Ne preklicuj</button></div>
     : <button type="button" className="secondary small" aria-label={`Prekliči povabilo za ${i.e_posta}`} disabled={busy} onClick={() => setCancelling(i.id)}><Icon name="close"/>Prekliči povabilo</button>}</td></tr>; })}
   </tbody></table></div></section>}
  {!loaded ? (error ? <button type="button" className="secondary" onClick={start}>Poskusi znova</button> : <p role="status" className="loading-state">Nalagam delavce …</p>) : !items.length ? <div className="empty-state"><h2>V podjetju še ni delavcev.</h2><p>Povabite prvega delavca z njegovo e-pošto.</p></div> : <>
   <div className="filter-bar">
    <label className="search-field">Poišči delavca<span className="search-wrap"><Icon name="search"/><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="E-pošta ali ime" autoComplete="off"/></span></label>
    <label>Stanje<select value={state} onChange={e => setState(e.target.value)}><option value="aktivni">Aktivni</option><option value="odvzeti">Odvzeti</option><option value="vsi">Vsi</option></select></label>
    <p className="result-count">{plural(shown.length, ['delavec', 'delavca', 'delavci', 'delavcev'])}</p>
   </div>
   {shown.length ? <div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">Delavci podjetja</caption><thead><tr><th>Delavec</th><th>Stanje</th><th className="num">Od</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {shown.map(w => <tr key={w.id} className={w.aktivna ? '' : 'muted'}><td><strong>{fullName(w)}</strong>{w.uporabnik_id === userId && <> <span className="status-badge pending">Vi</span></>}{fullName(w) !== w.e_posta && <span className="cell-detail">{w.e_posta}</span>}</td>
     <td><span className={`status-badge ${w.aktivna ? 'confirmed' : 'inactive'}`}>{w.aktivna ? 'Aktiven' : 'Odvzet'}</span></td><td className="num" data-label="Od:">{date(w.dodeljeno_ob)}</td>
     <td className="num">{!w.aktivna ? <button type="button" className="secondary small" aria-label={`Ponovno omogoči dostop delavcu ${w.e_posta}`} disabled={busy} onClick={() => change(w, true)}><Icon name="restore"/>Ponovno omogoči</button>
      : confirming === w.id ? <div className="row-confirm"><p>{`Odvzamem dostop delavcu ${w.e_posta}? Njegove vloge pri drugih podjetjih ostanejo nespremenjene.`}</p><button type="button" className="secondary small" disabled={busy} onClick={() => change(w, false)}><Icon name="revoke"/>Odvzemi dostop</button><button type="button" className="secondary small" onClick={() => setConfirming(null)}><Icon name="close"/>Prekliči</button></div>
      : <button type="button" className="secondary small" aria-label={`Odvzemi dostop delavcu ${w.e_posta}`} disabled={busy} onClick={() => setConfirming(w.id)}><Icon name="revoke"/>Odvzemi dostop</button>}</td></tr>)}
   </tbody></table></div> : <div className="empty-state"><p>Ni delavcev, ki ustrezajo iskanju.</p><button type="button" className="secondary" onClick={() => { setQuery(''); setState('aktivni'); }}>Počisti filtre</button></div>}
  </>}
 </>;
}
