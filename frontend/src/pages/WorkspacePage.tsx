import { useEffect, useRef, useState } from 'react';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import { getProfile, getCompanies } from '../features/identity/api';
import type { Profil, Podjetje } from '../features/identity/types';
import Admin from '../features/administration/components/Admin';
import MasterApplication from '../features/identity/components/MasterApplication';
import SupplierWorkspace from '../features/supplier/components/SupplierWorkspace';
import ProjectsWorkspace from '../features/projects/components/ProjectsWorkspace';
import MyProjects from '../features/projects/components/MyProjects';
import type { SupplierTab } from '../features/supplier/types';
import Brand from '../components/Brand';
import Icon from '../components/Icon';
import { ApiError } from '../services/api';
import IconButton from '../components/IconButton';

type View = SupplierTab | 'overview' | 'admin' | 'prosnja' | 'projekti' | 'moji';
export default function WorkspacePage({ client, session }: { client: SupabaseClient; session: Session }) {
 const [profile, setProfile] = useState<Profil | null>(null);
 const [companies, setCompanies] = useState<Podjetje[]>([]);
 const [companyId, setCompanyId] = useState('');
 const [view, setView] = useState<View>('overview');
 const [error, setError] = useState('');
 const [busy, setBusy] = useState(false);
 const [menu, setMenu] = useState(false);
 const request = useRef(0);
 async function load(background = false) {
  const sequence = ++request.current;
  // Keep the mounted workspace and unsaved forms during revalidation.
  if (!background) { setError(''); setBusy(true); }
  try {
   const [p, c] = await Promise.all([getProfile(client), getCompanies(client)]);
   if (sequence !== request.current) return;
   setError(''); setProfile(p); setCompanies(c);
   const own = c.filter(company => company.aktivno && p.vloge.some(role => role.podjetje_id === company.id && role.vloga === 'mojster'));
   setCompanyId(previous => own.some(company => company.id === previous) ? previous : own[0]?.id ?? '');
  } catch (e) {
   if (sequence !== request.current) return;
   if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
    setProfile(null); setCompanies([]);
    setError(e.message);
   } else {
    // A temporary outage does not mean that the user's access was revoked.
    // All business requests still require current server-side authorization.
    setError('Pravic trenutno ni mogoče osvežiti. Poskusite znova.');
   }
  }
  finally { if (sequence === request.current) setBusy(false); }
 }
 useEffect(() => {
  void load(true); const refresh = () => { void load(true); };
  window.addEventListener('focus', refresh);
  return () => { request.current++; window.removeEventListener('focus', refresh); };
 }, [client, session.access_token]);
 const admin = !!profile?.vloge.some(role => role.vloga === 'admin');
 const ownCompanies = companies.filter(company => company.aktivno && profile?.vloge.some(role => role.podjetje_id === company.id && role.vloga === 'mojster'));
 const company = ownCompanies.find(c => c.id === companyId);
 const supplier = !!company && !!profile?.vloge.some(role => role.podjetje_id === company.id && role.vloga === 'mojster');
 const activeView = view === 'admin' ? admin ? 'admin' : 'overview' : ['cenik','materiali','zaloge','projekti'].includes(view) ? supplier ? view : 'overview' : view;
 const customer = !!profile?.vloge.some(role => role.vloga === 'stranka');
 const shown = activeView === 'moji' && !customer ? 'overview' : activeView;
 const roleNames: Record<string, string> = { admin: 'Admin', stranka: 'Stranka', mojster: 'Mojster', delavec: 'Delavec' };
 const rolesAt = (id: string) => profile?.vloge.filter(role => role.podjetje_id === id).map(role => roleNames[role.vloga]).join(', ') ?? '';
 function go(next: View) { setView(next); setMenu(false); }
 const item = (id: View, icon: Parameters<typeof Icon>[0]['name'], label: string) => <button key={id} className={`nav-item ${activeView === id ? 'selected' : ''}`} aria-current={activeView === id ? 'page' : undefined} onClick={() => go(id)}><Icon name={icon}/>{label}</button>;
 return <div className={`shell ${menu ? 'menu-open' : ''}`}>
  <header className="mobile-bar"><IconButton icon={menu ? 'close' : 'menu'} label="Meni" tip={menu ? 'Zapri meni' : 'Odpri meni'} className="tip-right" aria-expanded={menu} aria-controls="app-menu" onClick={() => setMenu(!menu)}/><Brand/></header>
  <aside className="app-sidebar" id="app-menu"><Brand/>
   {!!ownCompanies.length && <label className="company-select">Aktivno podjetje<select value={companyId} disabled={busy} onChange={e => { setCompanyId(e.target.value); go('overview'); }}>{ownCompanies.map(c => <option key={c.id} value={c.id}>{c.naziv}</option>)}</select></label>}
   <nav aria-label="Glavna navigacija">{item('overview', 'grid', 'Pregled')}{customer && item('moji', 'list', 'Moji projekti')}{item('prosnja', 'user-plus', 'Prošnja za mojstra')}
    {supplier && <><p className="nav-label nav-group">Podatki podjetja</p>{item('cenik', 'list', 'Cenik')}{item('zaloge', 'stock', 'Zaloge')}{item('materiali', 'list', 'Materiali')}<p className="nav-label nav-group">Delo</p>{item('projekti', 'users', 'Projekti')}</>}
    {admin && <><p className="nav-label nav-group">Upravljanje</p>{item('admin', 'users', 'Podjetja in pravice')}</>}
   </nav>
   <div className="sidebar-bottom"><a className="sidebar-link" href="/demo"><Icon name="calculator"/>Demo kalkulator</a>
    <button className="sidebar-link" disabled={busy} onClick={() => void load()}><Icon name="refresh"/>Osveži pravice</button>
    <div className="account"><span className="avatar" aria-hidden="true">{(session.user.email ?? 'U').slice(0,1).toUpperCase()}</span><div><strong>Moj račun</strong><span>{session.user.email}</span></div><IconButton icon="logout" label="Odjava" onClick={async () => { const { error } = await client.auth.signOut(); if (error) setError('Odjava ni uspela. Poskusite znova.'); }}/></div>
   </div>
  </aside>
  <main className="app-main"><div className="sheet">{error && <p role="alert" className="alert">{error}</p>}{!profile && !error && <p role="status" className="loading-state">Preverjam dostop …</p>}
  {profile && <>{shown === 'moji' ? <MyProjects client={client}/> : shown === 'projekti' && supplier && company ? <ProjectsWorkspace key={company.id} client={client} companyId={company.id}/> : activeView === 'prosnja' ? <MasterApplication client={client}/> : activeView === 'admin' ? <Admin client={client}/> : supplier && company && (activeView === 'cenik' || activeView === 'zaloge' || activeView === 'materiali') ? <SupplierWorkspace key={company.id} client={client} companyId={company.id} tab={activeView}/> : <>
   <div className="page-title"><div><h1>{company ? company.naziv : 'Moj račun'}</h1><p>{company ? `Vaše vloge pri podjetju: ${rolesAt(company.id)}.` : 'Pregled vaših poslovnih dostopov. Projekti in ponudbe bodo na voljo v naslednjih sklopih.'}</p></div></div>
   {!profile.vloge.length ? <section className="empty-state"><h2>Dostop še ni dodeljen</h2><p>Račun je ustvarjen. Za podjetje potrebujete ustrezno dodelitev poslovne vloge.</p></section> : <div className="overview">
    <div className="overview-actions">
     {supplier && <section className="panel"><h2>Podatki za ponudbe</h2><p>Urejajte postavke dela, materiale in zaloge podjetja.</p><button onClick={() => go('cenik')}>Odpri cenik <Icon name="arrow"/></button></section>}
     {admin && <section className="panel"><h2>Administracija</h2><p>Upravljanje podjetij in dodelitev poslovnih vlog.</p><button className="secondary" onClick={() => go('admin')}>Podjetja in pravice <Icon name="arrow"/></button></section>}
    </div>
    <section className="membership-section"><h2>Moja podjetja</h2>{ownCompanies.length ? <div className="table-wrap"><table><thead><tr><th>Podjetje</th><th>Vaše vloge</th><th><span className="sr-only">Dejanje</span></th></tr></thead><tbody>{ownCompanies.map(c => <tr key={c.id}><td><strong>{c.naziv}</strong></td><td className="muted">{rolesAt(c.id)}</td><td>{companyId === c.id ? <span className="status-badge confirmed">Izbrano</span> : <IconButton icon="arrow" label={`Izberi ${c.naziv}`} tip="Izberi" onClick={() => { setCompanyId(c.id); go('overview'); }}/>}</td></tr>)}</tbody></table></div> : <p className="muted">Poslovna vloga pri podjetju vam ni dodeljena.</p>}</section>
   </div>}
  </>}</>}
  </div></main></div>;
}
