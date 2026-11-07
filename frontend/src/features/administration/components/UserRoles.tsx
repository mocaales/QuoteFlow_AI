import { useState } from 'react';
import type { ReactNode } from 'react';
import Icon from '../../../components/Icon';
import { fold, plural } from '../../../utils/format';
import type { Podjetje } from '../../identity/types';
import type { AdminRole, AdminUser } from '../types';
import { fullName, roleNames } from '../types';
import RoleAction from './RoleAction';
import RoleDrawer from './RoleDrawer';

type Props = { companies: Podjetje[]; users: AdminUser[]; roles: AdminRole[]; selected: string | null; busy: boolean; error: ReactNode; onSelect: (id: string | null) => void; onOpenCompany: (id: string) => void; onChange: (id: string, active: boolean, message: string) => void; onAssign: (uporabnik_id: string, podjetje_id: string, vloga: 'mojster' | 'delavec') => Promise<boolean>; onClearError: () => void };
const badge = (r: AdminRole) => <span className={`status-badge ${r.aktivna ? 'confirmed' : 'inactive'}`}>{r.aktivna ? 'Aktivna' : 'Odvzeta'}</span>;
export default function UserRoles({ companies, users, roles, selected, busy, error, onSelect, onOpenCompany, onChange, onAssign, onClearError }: Props) {
 const [query, setQuery] = useState(''), [role, setRole] = useState('vse'), [state, setState] = useState('aktivne'), [adding, setAdding] = useState(false);
 const own = (id: string) => roles.filter(r => r.uporabnik_id === id && r.aktivna);
 const shown = users.filter(u => (!query || fold(`${fullName(u)} ${u.e_posta}`).includes(fold(query))) && (role === 'vse' ? true : role === 'brez' ? !own(u.id).some(r => r.podjetje_id) : own(u.id).some(r => r.vloga === role)));
 const user = users.find(u => u.id === selected) ?? null;
 const mine = user ? roles.filter(r => r.uporabnik_id === user.id) : [];
 const isAdmin = mine.some(r => r.vloga === 'admin' && r.aktivna);
 const visible = (r: AdminRole) => state === 'vse' || r.aktivna === (state === 'aktivne');
 const global = mine.filter(r => r.vloga === 'stranka' && visible(r));
 const groups = [...new Set(mine.filter(r => r.podjetje_id && visible(r)).map(r => r.podjetje_id!))].map(id => ({ id, naziv: mine.find(r => r.podjetje_id === id)!.naziv ?? '', roles: mine.filter(r => r.podjetje_id === id && visible(r)) }));
 const summary = (id: string) => { const a = own(id), n = new Set(a.filter(r => r.podjetje_id).map(r => r.podjetje_id)).size; return `${a.some(r => r.vloga === 'stranka') ? 'Stranka · ' : ''}${plural(n, ['podjetje', 'podjetji', 'podjetja', 'podjetij'])}`; };
 return <div className="split" data-view={user ? 'detail' : 'list'}>
  <div className="split-list">
   <label className="search-field">Poišči uporabnika<span className="search-wrap"><Icon name="search"/><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="E-pošta, ime ali priimek" autoComplete="off"/></span></label>
   <div className="filter-bar"><label>Vloga<select value={role} onChange={e => setRole(e.target.value)}><option value="vse">Vse vloge</option><option value="stranka">Stranka</option><option value="mojster">Mojster</option><option value="delavec">Delavec</option><option value="brez">Brez poslovne vloge</option></select></label></div>
   <p className="result-count">{plural(shown.length, ['uporabnik', 'uporabnika', 'uporabniki', 'uporabnikov'])}</p>
   {shown.map(u => <button key={u.id} type="button" className="split-item" aria-current={u.id === selected} onClick={() => onSelect(u.id)}><span><strong>{fullName(u)}</strong><span className="cell-detail">{u.e_posta} · {summary(u.id)}</span></span></button>)}
   {!shown.length && <div className="empty-state"><p>Ni uporabnikov, ki ustrezajo iskanju.</p></div>}
  </div>
  <div className="split-detail">
   {!user ? <div className="empty-state"><p>Izberite uporabnika na levi.</p></div> : <>
    <button type="button" className="split-back" aria-label="Nazaj na seznam uporabnikov" onClick={() => onSelect(null)}>‹ Uporabniki</button>
    <div className="split-head"><h2>{fullName(user)}</h2>{isAdmin && <span className="status-badge confirmed">Skrbnik</span>}
     <button type="button" disabled={busy || isAdmin} onClick={() => setAdding(true)}><Icon name="user-plus"/>Dodeli vlogo</button></div>
    <p className="muted">{user.e_posta}</p>
    {isAdmin && <p className="owner-note">Skrbnik si ne more sam dodeliti vloge v podjetju.</p>}
    <div className="filter-bar"><label>Stanje<select value={state} onChange={e => setState(e.target.value)}><option value="aktivne">Aktivne</option><option value="odvzete">Odvzete</option><option value="vse">Vse</option></select></label></div>
    {!!global.length && <div role="group" aria-label="Globalno" className="role-card">{global.map(r => <div key={r.id} className="role-chip"><span>{roleNames[r.vloga]}</span>{badge(r)}</div>)}</div>}
    {groups.map(g => <div key={g.id} role="group" aria-labelledby={`g-${g.id}`} className="role-card"><div className="split-head"><h3 id={`g-${g.id}`}>{g.naziv}</h3><button type="button" className="text-button" aria-label={`Odpri podjetje ${g.naziv}`} onClick={() => onOpenCompany(g.id)}>Odpri<Icon name="arrow"/></button></div>
     {g.roles.map(r => <div key={r.id} className="role-chip"><span>{roleNames[r.vloga]}</span>{badge(r)}<RoleAction role={r} busy={busy} protectedNote={r.vloga === 'mojster' && (r.je_lastnik || companies.find(c => c.id === g.id)?.lastnik_id === r.uporabnik_id) ? `Lastnik podjetja ${g.naziv} ne more izgubiti vloge mojster.` : undefined} onChange={(active, message) => onChange(r.id, active, message)}/></div>)}</div>)}
    {!groups.length && !isAdmin && <div className="empty-state"><p>{mine.some(r => r.podjetje_id) ? 'Ni vlog, ki ustrezajo filtru.' : 'Uporabnik nima poslovnih vlog.'}</p></div>}
   </>}
  </div>
  {adding && user && <RoleDrawer title="Dodeli vlogo" busy={busy} error={error} onClose={() => { setAdding(false); onClearError(); }} onSubmit={async (vloga, data) => { if (await onAssign(user.id, String(data.get('podjetje_id')), vloga)) setAdding(false); }}
   pick={() => <label>Podjetje<select name="podjetje_id" required defaultValue=""><option value="" disabled>Izberite podjetje</option>{companies.filter(c => c.aktivno).map(c => <option key={c.id} value={c.id}>{c.naziv}</option>)}</select></label>}/>}
 </div>;
}
