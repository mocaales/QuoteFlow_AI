import { useEffect, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { getCompanies } from '../../identity/api';
import type { Podjetje, Uporabnik, Dodelitev, ProsnjaAdmin } from '../../identity/types';
import { getUsers, getRoles, getApplications, decideApplication, saveCompany, assignRole, setRoleActive } from '../api';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { dateTime } from '../../../utils/format';

const roleNames: Record<Dodelitev['vloga'], string> = { admin: 'Admin', stranka: 'Stranka', mojster: 'Mojster', delavec: 'Delavec' };
export default function Admin({ client }: { client: SupabaseClient }) {
 const [companies, setCompanies] = useState<Podjetje[]>([]);
 const [users, setUsers] = useState<Uporabnik[]>([]);
 const [roles, setRoles] = useState<Dodelitev[]>([]);
 const [applications, setApplications] = useState<ProsnjaAdmin[]>([]);
 const [edit, setEdit] = useState<Podjetje | null>(null);
 const [name, setName] = useState('');
 const [status, setStatus] = useState(true);
 const [role, setRole] = useState('stranka');
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [loading, setLoading] = useState(true);
 async function load() {
  const [c, u, r, a] = await Promise.all([getCompanies(client), getUsers(client), getRoles(client), getApplications(client)]);
  setCompanies(c); setUsers(u); setRoles(r); setApplications(Array.isArray(a) ? a : []);
 }
 useEffect(() => { let active = true; load().catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [client]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setNotice(message); }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 function submitCompany(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const data = new FormData(e.currentTarget);
  void mutate(async () => {
   await saveCompany(client, edit, { naziv:name.trim(), lastnik_id:edit?.lastnik_id ?? String(data.get('lastnik')), maticna_stevilka:String(data.get('maticna')).trim(), davcna_stevilka:String(data.get('davcna')).trim() || null, naslov:String(data.get('naslov')).trim(), aktivno:status });
   setEdit(null); setName(''); setStatus(true);
  }, 'Podjetje je shranjeno.');
 }
 function assign(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const data = Object.fromEntries(new FormData(e.currentTarget));
  void mutate(() => assignRole(client, { ...data, podjetje_id: role === 'stranka' ? null : data.podjetje_id }), 'Poslovna vloga je dodeljena.');
 }
 return <>
  <div className="page-title"><div><h1>Podjetja in pravice</h1><p>{loading ? 'Upravljajte podjetja in dostop registriranih uporabnikov.' : `${companies.filter(c => c.aktivno).length} aktivnih podjetij in ${roles.filter(r => r.aktivna).length} aktivnih dodelitev vlog.`}</p></div></div>
  {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
  {loading ? <p role="status" className="loading-state">Nalagam podatke …</p> : <>
  <section className="admin-section"><h2>Prošnje mojstrov</h2>
   <div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">Prošnje za mojstra</caption><thead><tr><th>Podjetje</th><th>Vlagatelj</th><th className="num">Oddano</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {applications.map(a => <tr key={a.id}><td><strong>{a.naziv_podjetja}</strong><span className="muted"> · {a.maticna_stevilka}</span></td><td data-label="Vlagatelj:">{a.e_posta}</td><td className="num" data-label="Oddano:">{dateTime(a.oddano_ob)}</td><td><span className={`status-badge ${a.stanje === 'oddana' ? 'pending' : a.stanje === 'odobrena' ? 'confirmed' : 'inactive'}`}>{a.stanje === 'oddana' ? 'Oddana' : a.stanje === 'odobrena' ? 'Odobrena' : 'Zavrnjena'}</span></td><td className="num">{a.stanje === 'oddana' && <><IconButton icon="check" label={`Odobri ${a.naziv_podjetja}`} tip="Odobri" disabled={busy} onClick={() => void mutate(() => decideApplication(client, a.id, true), 'Prošnja je odobrena.')}/><IconButton icon="close" label={`Zavrni ${a.naziv_podjetja}`} tip="Zavrni" disabled={busy} onClick={() => void mutate(() => decideApplication(client, a.id, false), 'Prošnja je zavrnjena.')}/></>}</td></tr>)}
    {!applications.length && <tr><td colSpan={5} className="muted">Prošenj še ni.</td></tr>}
   </tbody></table></div>
  </section>
  <section className="admin-section narrow"><h2>Podjetja</h2>
   <form className="inline-form" onSubmit={submitCompany}>
    <label>Naziv podjetja<input value={name} onChange={e => setName(e.target.value)} required maxLength={200}/></label>
    {!edit && <label>Lastnik podjetja<select name="lastnik" required defaultValue=""><option value="" disabled>Izberite lastnika</option>{users.map(u => <option key={u.id} value={u.id}>{u.e_posta}</option>)}</select></label>}
    <label>Matična številka<input key={`maticna-${edit?.id ?? 'new'}`} name="maticna" defaultValue={edit?.maticna_stevilka} required maxLength={30}/></label>
    <label>Davčna številka<input key={`davcna-${edit?.id ?? 'new'}`} name="davcna" defaultValue={edit?.davcna_stevilka ?? ''} maxLength={30}/></label>
    <label>Naslov podjetja<input key={`naslov-${edit?.id ?? 'new'}`} name="naslov" defaultValue={edit?.naslov} required maxLength={500}/></label>
    {edit && <label>Stanje<select value={status ? 'aktivno' : 'neaktivno'} onChange={e => setStatus(e.target.value === 'aktivno')}><option value="aktivno">Aktivno</option><option value="neaktivno">Neaktivno</option></select></label>}
    <button disabled={busy || !name.trim()}><Icon name={edit ? 'check' : 'plus'}/>{edit ? 'Shrani spremembe' : 'Dodaj podjetje'}</button>
    {edit && <button type="button" className="secondary" onClick={() => { setEdit(null); setName(''); setStatus(true); }}><Icon name="close"/>Prekliči</button>}
   </form>
   <div className="table-wrap"><table className="data-table"><caption className="sr-only">Registrirana podjetja</caption><thead><tr><th>Naziv</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {companies.map(c => <tr key={c.id}><td><strong>{c.naziv}</strong></td><td><span className={`status-badge ${c.aktivno ? 'confirmed' : 'inactive'}`}>{c.aktivno ? 'Aktivno' : 'Neaktivno'}</span></td><td className="num"><IconButton icon="pen" label={`Uredi ${c.naziv}`} tip="Uredi" disabled={busy} onClick={() => { setEdit(c); setName(c.naziv); setStatus(c.aktivno); }}/></td></tr>)}
    {!companies.length && <tr><td colSpan={3} className="muted">Podjetij še ni. Dodajte prvo podjetje.</td></tr>}
   </tbody></table></div>
  </section>
  <section className="admin-section"><h2>Uporabniki in poslovne vloge</h2><p className="muted">Uporabnik se najprej registrira. Stranka je globalna vloga. Mojster in delavec imata pravice samo pri izbranem podjetju.</p>
   <form className="inline-form" onSubmit={assign}>
    <label>Uporabnik<select name="uporabnik_id" required defaultValue=""><option value="" disabled>Izberite uporabnika</option>{users.map(u => <option key={u.id} value={u.id}>{u.e_posta}</option>)}</select></label>
    <label>Podjetje<select name="podjetje_id" disabled={role === 'stranka'} required={role !== 'stranka'} defaultValue=""><option value="" disabled>Izberite podjetje</option>{companies.filter(c => c.aktivno).map(c => <option key={c.id} value={c.id}>{c.naziv}</option>)}</select></label>
    <label>Vloga<select name="vloga" value={role} onChange={e => setRole(e.target.value)}><option value="stranka">Stranka</option><option value="mojster">Mojster</option><option value="delavec">Delavec</option></select></label>
    <button disabled={busy || !users.length || (role !== 'stranka' && !companies.some(c => c.aktivno))}><Icon name="user-plus"/>Dodeli vlogo</button>
   </form>
   <div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">Dodelitve uporabniških vlog</caption><thead><tr><th>Uporabnik</th><th>Podjetje</th><th>Vloga</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {roles.map(r => <tr key={r.id}><td><strong>{r.e_posta}</strong></td><td className={r.naziv ? '' : 'muted'}>{r.naziv || 'Globalna vloga'}</td><td data-label="Vloga:">{roleNames[r.vloga]}</td><td><span className={`status-badge ${r.aktivna ? 'confirmed' : 'inactive'}`}>{r.aktivna ? 'Aktivna' : 'Odvzeta'}</span></td><td className="num">{r.vloga !== 'admin' && <IconButton icon={r.aktivna ? 'revoke' : 'restore'} label={r.aktivna ? 'Odvzemi' : 'Aktiviraj'} tip={r.aktivna ? 'Odvzemi vlogo' : 'Ponovno aktiviraj'} disabled={busy} onClick={() => void mutate(() => setRoleActive(client, r.id, !r.aktivna), r.aktivna ? 'Vloga je odvzeta.' : 'Vloga je ponovno aktivna.')}/>}</td></tr>)}
    {!roles.length && <tr><td colSpan={5} className="muted">Dodeljenih vlog še ni.</td></tr>}
   </tbody></table></div>
  </section></>}
 </>;
}
