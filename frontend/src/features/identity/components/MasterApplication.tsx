import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { getApplications, submitApplication } from '../api';
import type { Prosnja } from '../types';
import Icon from '../../../components/Icon';
import { dateTime } from '../../../utils/format';

const states: Record<Prosnja['stanje'], { label: string; badge: string }> = { oddana: { label: 'Oddana', badge: 'pending' }, odobrena: { label: 'Odobrena', badge: 'confirmed' }, zavrnjena: { label: 'Zavrnjena', badge: 'inactive' } };
export default function MasterApplication({ client }: { client: SupabaseClient }) {
 const [items, setItems] = useState<Prosnja[]>([]);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const request = useRef(0);
 async function load() {
  const sequence = ++request.current;
  const data = await getApplications(client);
  if (sequence === request.current) setItems(data);
 }
 useEffect(() => { load().catch(e => setError(e instanceof Error ? e.message : 'Prošenj ni mogoče naložiti.')).finally(() => setLoading(false)); return () => { request.current++; }; }, [client]);
 async function submit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const form = e.currentTarget; const data = new FormData(form); const text = (name: string) => String(data.get(name) ?? '').trim();
  setBusy(true); setError(''); setNotice('');
  try {
   await submitApplication(client, { naziv_podjetja: text('naziv'), maticna_stevilka: text('maticna'), davcna_stevilka: text('davcna') || null, naslov_podjetja: text('naslov') });
   form.reset(); setNotice('Prošnja je oddana. Administrator jo bo pregledal.'); await load();
  } catch (err) { setError(err instanceof Error ? err.message : 'Prošnje ni mogoče oddati.'); }
  finally { setBusy(false); }
 }
 const pending = items.some(i => i.stanje === 'oddana');
 return <>
  <div className="page-title"><div><h1>Prošnja za mojstra</h1><p>Za upravljanje cenika, materialov in zalog podjetja oddajte prošnjo. Administrator jo bo pregledal.</p></div></div>
  {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
  {loading ? <p role="status" className="loading-state">Nalagam prošnje …</p> : <>
  {!!items.length && <section className="admin-section"><h2>Moje prošnje</h2><div className="table-wrap"><table className="data-table"><caption className="sr-only">Moje prošnje za mojstra</caption><thead><tr><th>Podjetje</th><th>Stanje</th><th className="num">Oddano</th></tr></thead><tbody>
   {items.map(i => <tr key={i.id}><td><strong>{i.naziv_podjetja}</strong><span className="muted"> · {i.maticna_stevilka}</span></td><td><span className={`status-badge ${states[i.stanje].badge}`}>{states[i.stanje].label}</span></td><td className="num" data-label="Oddano:">{dateTime(i.oddano_ob)}</td></tr>)}
  </tbody></table></div></section>}
  {pending ? <p className="muted">Imate oddano prošnjo, ki še čaka na odločitev.</p> : <section className="admin-section narrow"><h2>Nova prošnja</h2>
   <form className="inline-form" onSubmit={e => void submit(e)}>
    <label>Naziv podjetja<input name="naziv" required maxLength={200}/></label>
    <label>Matična številka<input name="maticna" required maxLength={30}/></label>
    <label>Naslov podjetja<input name="naslov" required maxLength={300}/></label>
    <label>Davčna številka (neobvezno)<input name="davcna" maxLength={30}/></label>
    <button disabled={busy}><Icon name="check"/>Oddaj prošnjo</button>
   </form>
  </section>}
  </>}
 </>;
}
