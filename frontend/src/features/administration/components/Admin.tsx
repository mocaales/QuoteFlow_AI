import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { getCompanies } from '../../identity/api';
import type { Podjetje, ProsnjaAdmin } from '../../identity/types';
import { getUsers, getRoles, getApplications, decideApplication, saveCompany, assignRole, setRoleActive, type CompanyInput } from '../api';
import type { AdminRole, AdminUser } from '../types';
import Applications from './Applications';
import Companies from './Companies';
import CompanyRoles from './CompanyRoles';
import UserRoles from './UserRoles';

type Tab = 'podjetja' | 'uporabniki' | 'prosnje' | 'seznam';
export default function Admin({ client }: { client: SupabaseClient }) {
 const [companies, setCompanies] = useState<Podjetje[]>([]);
 const [users, setUsers] = useState<AdminUser[]>([]);
 const [roles, setRoles] = useState<AdminRole[]>([]);
 const [applications, setApplications] = useState<ProsnjaAdmin[]>([]);
 const [tab, setTab] = useState<Tab>('podjetja');
 const [company, setCompany] = useState<string | null>(null);
 const [user, setUser] = useState<string | null>(null);
 const [loaded, setLoaded] = useState(false);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const seq = useRef(0);
 const load = useCallback(async () => {
  const id = ++seq.current;
  const [c, u, r, a] = await Promise.all([getCompanies(client), getUsers(client), getRoles(client), getApplications(client)]);
  if (id !== seq.current) return;
  setCompanies(c); setUsers(u); setRoles(r); setApplications(Array.isArray(a) ? a : []);
 }, [client]);
 const start = useCallback(() => { setError(''); setLoaded(false); load().then(() => setLoaded(true), e => setError(e instanceof Error ? e.message : 'Podatkov ni mogoče naložiti.')); }, [load]);
 useEffect(() => { start(); return () => { seq.current++; }; }, [start]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setNotice(message); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 const change = (id: string, active: boolean, message: string) => void mutate(() => setRoleActive(client, id, active), message);
 const assign = (uporabnik_id: string, podjetje_id: string, vloga: 'mojster' | 'delavec') => mutate(() => assignRole(client, { uporabnik_id, podjetje_id, vloga }), 'Vloga je dodeljena.');
 const save = (item: Podjetje | null, data: CompanyInput) => mutate(() => saveCompany(client, item, data), 'Podjetje je shranjeno.');
 const pending = applications.filter(a => a.stanje === 'oddana').length;
 const tabs: [Tab, string][] = [['podjetja', 'Po podjetjih'], ['uporabniki', 'Po uporabnikih'], ['prosnje', 'Prošnje mojstrov'], ['seznam', 'Podjetja']];
 function keys(e: KeyboardEvent) {
  const i = tabs.findIndex(t => t[0] === tab), next = e.key === 'ArrowRight' ? (i + 1) % tabs.length : e.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : -1;
  if (next < 0) return;
  e.preventDefault(); setTab(tabs[next][0]); document.getElementById(`admin-tab-${tabs[next][0]}`)?.focus();
 }
 const alert = error ? <p role="alert" className="alert">{error}</p> : null;
 const drawerOpen = () => document.querySelector('dialog[open]') !== null;
 return <>
  <div className="page-title"><div><h1>Podjetja in pravice</h1><p>Kdo ima kje katero vlogo, in kako to spremenim?</p></div></div>
  {!loaded ? (error ? <>{alert}<button type="button" className="secondary" onClick={start}>Poskusi znova</button></> : <p role="status" className="loading-state">Nalagam podatke …</p>) : <>
   {notice && <p role="status" className="notice">{notice}</p>}
   {!drawerOpen() && alert}
   <div className="tabs" role="tablist" aria-label="Pogledi" onKeyDown={keys}>
    {tabs.map(([id, label]) => <button key={id} id={`admin-tab-${id}`} type="button" role="tab" className="tab" aria-selected={tab === id} aria-controls="admin-panel" tabIndex={tab === id ? 0 : -1} onClick={() => { setTab(id); setNotice(''); }}>{label}{id === 'prosnje' && pending > 0 && <> <span className="count">({pending})</span></>}</button>)}
   </div>
   <div id="admin-panel" role="tabpanel" aria-labelledby={`admin-tab-${tab}`} className="admin-section">
    {tab === 'podjetja' && <CompanyRoles companies={companies} users={users} roles={roles} selected={company} busy={busy} error={alert} onSelect={setCompany} onChange={change} onAssign={assign} onClearError={() => setError('')}/>}
    {tab === 'uporabniki' && <UserRoles companies={companies} users={users} roles={roles} selected={user} busy={busy} error={alert} onSelect={setUser} onOpenCompany={id => { setCompany(id); setTab('podjetja'); }} onChange={change} onAssign={assign} onClearError={() => setError('')}/>}
    {tab === 'prosnje' && <Applications items={applications} busy={busy} onDecide={(id, approve) => void mutate(() => decideApplication(client, id, approve), approve ? 'Prošnja je odobrena.' : 'Prošnja je zavrnjena.')}/>}
    {tab === 'seznam' && <Companies companies={companies} users={users} busy={busy} error={alert} onSave={save} onClearError={() => setError('')}/>}
   </div>
  </>}
 </>;
}
