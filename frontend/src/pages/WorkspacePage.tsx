import { useEffect, useState } from 'react';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import { getProfile, getCompanies } from '../features/identity/api';
import type { Profil, Podjetje } from '../features/identity/types';
import Admin from '../features/administration/components/Admin';
import Brand from '../components/Brand';

export default function WorkspacePage({ client, session }: { client: SupabaseClient; session: Session }) {
 const [profile, setProfile] = useState<Profil | null>(null);
 const [companies, setCompanies] = useState<Podjetje[]>([]);
 const [error, setError] = useState('');
 const [busy, setBusy] = useState(false);
 async function load() {
  setError(''); setBusy(true);
  try {
   const p = await getProfile(client);
   setProfile(p); setCompanies(await getCompanies(client));
  } catch (e) { setProfile(null); setCompanies([]); setError(e instanceof Error ? e.message : 'Podatki niso na voljo.'); }
  finally { setBusy(false); }
 }
 useEffect(() => {
  void load(); const refresh = () => { void load(); };
  window.addEventListener('focus', refresh);
  return () => window.removeEventListener('focus', refresh);
 }, [client, session.access_token]);
 const admin = profile?.vloge.some(v => v.vloga === 'administrator');
 return <div className="shell"><aside><Brand/><p className="muted">Delovni prostor</p>
  <nav aria-label="Glavna navigacija"><a href="/" aria-current="page">{admin ? 'Podjetja in pravice' : 'Moja podjetja'}</a><a href="/demo">Demonstracija kalkulatorja</a></nav>
  <div className="sidebar-bottom account"><span>{session.user.email}</span><button className="text-button" onClick={async () => { const { error } = await client.auth.signOut(); if (error) setError('Odjava ni uspela. Poskusite znova.'); }}>Odjava</button></div>
 </aside><main><header><span>QuoteFlow / {admin ? 'Administracija' : 'Moj račun'}</span><button className="text-button" disabled={busy} onClick={() => void load()}>Osveži pravice</button></header>
  {error && <p role="alert" className="alert">{error}</p>}
  {!profile && !error && <p role="status">Preverjam dostop …</p>}
  {profile && (admin ? <Admin client={client}/> : <>
   <div className="page-title"><p className="eyebrow">MOJ RAČUN</p><h1>Moja podjetja</h1></div>
   {!profile.vloge.length ? <section className="empty-state"><h2>Dostop še ni dodeljen</h2><p>Račun je ustvarjen. Administrator vam mora dodeliti poslovno vlogo pri podjetju.</p></section> : <div className="table-wrap"><table><thead><tr><th>Podjetje</th><th>Vaše vloge</th></tr></thead><tbody>{companies.map(c => <tr key={c.id}><td>{c.naziv}</td><td>{profile.vloge.filter(v => v.podjetje_id === c.id).map(v => v.vloga).join(', ')}</td></tr>)}</tbody></table></div>}
  </>)}
 </main></div>;
}
