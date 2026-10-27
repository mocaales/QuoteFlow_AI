import { useEffect, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { getCompanies } from '../../identity/api';
import type { Podjetje, Uporabnik, Dodelitev } from '../../identity/types';
import { getUsers, getRoles, saveCompany, assignRole, setRoleActive } from '../api';

export default function Admin({ client }: { client: SupabaseClient }) {
 const [companies, setCompanies] = useState<Podjetje[]>([]);
 const [users, setUsers] = useState<Uporabnik[]>([]);
 const [roles, setRoles] = useState<Dodelitev[]>([]);
 const [edit, setEdit] = useState<Podjetje | null>(null);
 const [name, setName] = useState('');
 const [status, setStatus] = useState<'aktivno' | 'neaktivno'>('aktivno');
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [loading, setLoading] = useState(true);
 async function load() {
  const [c, u, r] = await Promise.all([getCompanies(client), getUsers(client), getRoles(client)]);
  setCompanies(c); setUsers(u); setRoles(r);
 }
 useEffect(() => { let active = true; load().catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [client]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setNotice(message); }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 function submitCompany(e: FormEvent<HTMLFormElement>) {
  e.preventDefault();
  void mutate(async () => {
   await saveCompany(client, edit, name.trim(), status);
   setEdit(null); setName(''); setStatus('aktivno');
  }, 'Podjetje je shranjeno.');
 }
 function assign(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const data = Object.fromEntries(new FormData(e.currentTarget));
  void mutate(() => assignRole(client, data), 'Poslovna vloga je dodeljena.');
 }
 return <>
  <div className="page-title"><p className="eyebrow">ADMINISTRACIJA</p><h1>Podjetja in pravice</h1><p className="muted">Upravljajte podjetja in dostop registriranih uporabnikov.</p></div>
  {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
  {loading ? <p role="status">Nalagam podatke …</p> : <>
  <section className="admin-section"><h2>Podjetja</h2>
   <form className="inline-form" onSubmit={submitCompany}>
    <label>Naziv podjetja<input value={name} onChange={e => setName(e.target.value)} required maxLength={200}/></label>
    {edit && <label>Stanje<select value={status} onChange={e => setStatus(e.target.value as typeof status)}><option value="aktivno">Aktivno</option><option value="neaktivno">Neaktivno</option></select></label>}
    <button disabled={busy || !name.trim()}>{edit ? 'Shrani spremembe' : 'Dodaj podjetje'}</button>
    {edit && <button type="button" className="secondary" onClick={() => { setEdit(null); setName(''); setStatus('aktivno'); }}>Prekliči</button>}
   </form>
   <div className="table-wrap"><table><caption className="sr-only">Registrirana podjetja</caption><thead><tr><th>Naziv</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {companies.map(c => <tr key={c.id}><td>{c.naziv}</td><td>{c.stanje === 'aktivno' ? 'Aktivno' : 'Neaktivno'}</td><td><button type="button" disabled={busy} className="text-button" aria-label={`Uredi ${c.naziv}`} onClick={() => { setEdit(c); setName(c.naziv); setStatus(c.stanje); }}>Uredi</button></td></tr>)}
    {!companies.length && <tr><td colSpan={3}>Podjetij še ni. Dodajte prvo podjetje.</td></tr>}
   </tbody></table></div>
  </section>
  <section className="admin-section"><h2>Uporabniki in poslovne vloge</h2><p className="muted">Uporabnik se najprej registrira. Vsaka poslovna vloga velja za izbrano podjetje.</p>
   <form className="inline-form" onSubmit={assign}>
    <label>Uporabnik<select name="uporabnik_id" required defaultValue=""><option value="" disabled>Izberite uporabnika</option>{users.map(u => <option key={u.id} value={u.id}>{u.e_posta}</option>)}</select></label>
    <label>Podjetje<select name="podjetje_id" required defaultValue=""><option value="" disabled>Izberite podjetje</option>{companies.filter(c => c.stanje === 'aktivno').map(c => <option key={c.id} value={c.id}>{c.naziv}</option>)}</select></label>
    <label>Vloga<select name="vloga" defaultValue="nabavnik"><option value="nabavnik">Nabavnik</option><option value="ponudnik">Ponudnik</option></select></label>
    <button disabled={busy || !users.length || !companies.some(c => c.stanje === 'aktivno')}>Dodeli vlogo</button>
   </form>
   <div className="table-wrap"><table><caption className="sr-only">Dodelitve uporabniških vlog</caption><thead><tr><th>Uporabnik</th><th>Podjetje</th><th>Vloga</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {roles.map(r => <tr key={r.id}><td>{r.e_posta}</td><td>{r.naziv || 'Globalna vloga'}</td><td>{r.vloga}</td><td>{r.aktivna ? 'Aktivna' : 'Odvzeta'}</td><td>{r.vloga !== 'administrator' && <button className="text-button" disabled={busy} onClick={() => void mutate(() => setRoleActive(client, r.id, !r.aktivna), r.aktivna ? 'Vloga je odvzeta.' : 'Vloga je ponovno aktivna.')}>{r.aktivna ? 'Odvzemi' : 'Aktiviraj'}</button>}</td></tr>)}
    {!roles.length && <tr><td colSpan={5}>Dodeljenih vlog še ni.</td></tr>}
   </tbody></table></div>
  </section></>}
 </>;
}
