import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Icon from '../../../components/Icon';
import { ApiError } from '../../../services/api';
import { getInvoice, issueInvoice, payInvoice } from '../api';
import type { Invoice } from '../types';
import InvoiceDocument from './InvoiceDocument';

const pad = (n: number) => String(n).padStart(2, '0');
function defaultDue() { const d = new Date(); d.setDate(d.getDate() + 8); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }

export default function InvoicePanel({ client, companyId, projectId, izvedbaKoncana, prejemnik, naslov }: { client: SupabaseClient; companyId: string; projectId: string; izvedbaKoncana: boolean; prejemnik: string; naslov: string }) {
 const [invoice, setInvoice] = useState<Invoice | null>(null);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [loadFailed, setLoadFailed] = useState(false);
 const [confirming, setConfirming] = useState(false);
 const form = useRef<HTMLFormElement>(null), group = useRef<HTMLDivElement>(null), issueButton = useRef<HTMLButtonElement>(null), asked = useRef(false);
 const sequence = useRef(0), heading = useRef<HTMLHeadingElement>(null);
 useEffect(() => {
  const request = ++sequence.current;
  getInvoice(client, companyId, projectId).then(next => { if (request === sequence.current) setInvoice(next); })
   .catch(e => { if (request !== sequence.current || (e instanceof ApiError && e.status === 404)) return; setLoadFailed(true); setError(e instanceof Error ? e.message : 'Računa ni mogoče naložiti.'); })
   .finally(() => { if (request === sequence.current) setLoading(false); });
  return () => { sequence.current++; };
 }, [client, companyId, projectId]);
 async function run(action: () => Promise<Invoice>) {
  const from = document.activeElement as HTMLElement | null;
  setBusy(true); setError(''); heading.current?.focus(); // a disabled focused button would drop focus to <body> while the request runs
  try { const next = await action(); setInvoice(next); heading.current?.focus(); }
  catch (e) { setError(e instanceof Error ? e.message : 'Dejanja ni mogoče izvesti.'); if (from?.isConnected) setTimeout(() => from.focus()); }
  finally { setBusy(false); }
 }
 useEffect(() => {
  if (confirming) { asked.current = true; group.current?.querySelector('button')?.focus(); }
  else if (asked.current) { asked.current = false; issueButton.current?.focus(); }
 }, [confirming]);
 const values = () => { const data = new FormData(form.current!); return { prejemnik_naziv: String(data.get('prejemnik_naziv') ?? '').trim(), prejemnik_naslov: String(data.get('prejemnik_naslov') ?? '').trim(), zapade_dne: String(data.get('zapade_dne') ?? '') }; };
 function ask(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const v = values();
  if (!v.prejemnik_naziv) { setError('Vnesite prejemnika računa.'); return; }
  if (!v.prejemnik_naslov) { setError('Vnesite naslov prejemnika.'); return; }
  if (!v.zapade_dne) { setError('Vnesite rok plačila.'); return; }
  setError(''); setConfirming(true);
 }
 async function issue() { await run(() => issueInvoice(client, companyId, projectId, values())); setConfirming(false); }
 const alert = error && <ActionAlert>{error}</ActionAlert>;
 if (loading) return <div className="loading-state" role="status">Nalagam račun …</div>;
 if (loadFailed) return alert;
 if (!invoice) return <section className="panel"><h2>Račun</h2><p>Osnutek računa bo pripravljen po sprejeti ponudbi.</p></section>;
 const draft = invoice.stanje_dokumenta === 'osnutek', unpaid = !draft && invoice.stanje_placila !== 'placan';
 return <InvoiceDocument invoice={invoice} headingRef={heading}>
  {alert}
  {draft && (izvedbaKoncana
   ? <form ref={form} className="editor-form" noValidate onSubmit={ask}>
    <label>Prejemnik<input name="prejemnik_naziv" maxLength={200} required defaultValue={prejemnik} readOnly={confirming}/></label>
    <label>Naslov prejemnika<input name="prejemnik_naslov" maxLength={300} required defaultValue={naslov} readOnly={confirming}/></label>
    <label>Rok plačila<input name="zapade_dne" type="date" required defaultValue={defaultDue()} readOnly={confirming}/></label>
    {confirming
     ? <div className="row-actions" role="group" aria-label="Potrditev izdaje" ref={group} onKeyDown={e => { if (e.key === 'Escape' && !busy) setConfirming(false); }}><p>Po izdaji računa ne bo več mogoče spreminjati. Ali ga res želite izdati?</p><button type="button" disabled={busy} onClick={() => void issue()}><Icon name="check"/>Potrdi izdajo</button><button type="button" className="secondary" disabled={busy} onClick={() => setConfirming(false)}>Prekliči</button></div>
     : <div className="row-actions"><button type="submit" ref={issueButton} disabled={busy}><Icon name="check"/>Izdaj račun</button></div>}
   </form>
   : <div className="row-actions"><p className="muted">Račun je mogoče izdati po zaključeni izvedbi.</p><button type="button" disabled><Icon name="check"/>Izdaj račun</button></div>)}
  {unpaid && <div className="row-actions"><button type="button" disabled={busy} onClick={() => void run(() => payInvoice(client, companyId, projectId))}><Icon name="check"/>Evidentiraj plačilo</button></div>}
 </InvoiceDocument>;
}
