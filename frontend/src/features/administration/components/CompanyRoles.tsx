import { useState } from 'react';
import type { ReactNode } from 'react';
import Icon from '../../../components/Icon';
import { fold, plural } from '../../../utils/format';
import type { Podjetje } from '../../identity/types';
import type { AdminRole, AdminUser } from '../types';
import { fullName, roleNames } from '../types';
import RoleAction from './RoleAction';
import RoleDrawer from './RoleDrawer';

type Props = { companies: Podjetje[]; users: AdminUser[]; roles: AdminRole[]; selected: string | null; busy: boolean; error: ReactNode; onSelect: (id: string | null) => void; onChange: (id: string, active: boolean, message: string) => void; onAssign: (uporabnik_id: string, podjetje_id: string, vloga: 'mojster' | 'delavec') => Promise<boolean>; onClearError: () => void };
export default function CompanyRoles({ companies, users, roles, selected, busy, error, onSelect, onChange, onAssign, onClearError }: Props) {
 const [query, setQuery] = useState(''), [search, setSearch] = useState(''), [role, setRole] = useState('vse'), [state, setState] = useState('aktivne'), [adding, setAdding] = useState(false);
 const company = companies.find(c => c.id === selected) ?? null;
 const shown = companies.filter(c => !query || fold(`${c.naziv} ${c.maticna_stevilka}`).includes(fold(query)));
 const members = company ? roles.filter(r => r.podjetje_id === company.id && (role === 'vse' || r.vloga === role) && (state === 'vse' || r.aktivna === (state === 'aktivne')) && (!search || fold(`${fullName(r)} ${r.e_posta}`).includes(fold(search)))) : [];
 const owner = company && users.find(u => u.id === company.lastnik_id);
 const admins = new Set(roles.filter(r => r.vloga === 'admin' && r.aktivna).map(r => r.uporabnik_id));
 const options = (vloga: string) => company ? users.filter(u => u.potrjen !== false && !roles.some(r => r.podjetje_id === company.id && r.uporabnik_id === u.id && r.aktivna && r.vloga === vloga)) : [];
 const count = (id: string) => roles.filter(r => r.podjetje_id === id && r.aktivna).length;
 return <div className="split" data-view={company ? 'detail' : 'list'}>
  <div className="split-list">
   <label className="search-field"><span className="sr-only">Poišči podjetje</span><Icon name="search"/><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Naziv ali matična številka" autoComplete="off"/></label>
   <p className="result-count">{plural(shown.length, ['podjetje', 'podjetji', 'podjetja', 'podjetij'])}</p>
   {shown.map(c => <button key={c.id} type="button" className="split-item" aria-current={c.id === selected} onClick={() => onSelect(c.id)}><span><strong>{c.naziv}</strong><span className="cell-detail">Aktivnih: {count(c.id)}</span></span>{!c.aktivno && <span className="status-badge inactive">Neaktivno</span>}</button>)}
   {!shown.length && (companies.length ? <div className="empty-state"><p>{`Ni zadetkov za »${query}«.`}</p><button type="button" className="secondary" onClick={() => setQuery('')}>Počisti iskanje</button></div> : <div className="empty-state"><p>Podjetij še ni.</p></div>)}
  </div>
  <div className="split-detail">
   {!company ? <div className="empty-state"><p>Izberite podjetje na levi.</p></div> : <>
    <button type="button" className="split-back" onClick={() => onSelect(null)}>‹ Podjetja</button>
    <div className="split-head"><h2>{company.naziv}</h2><span className={`status-badge ${company.aktivno ? 'confirmed' : 'inactive'}`}>{company.aktivno ? 'Aktivno' : 'Neaktivno'}</span>
     <button type="button" disabled={busy || !company.aktivno} onClick={() => setAdding(true)}><Icon name="user-plus"/>Dodaj člana</button></div>
    <p className="muted">{`mat. ${company.maticna_stevilka}${owner ? ` · Lastnik: ${owner.e_posta}` : ''}`}</p>
    {!company.aktivno && <p className="owner-note">Podjetje je neaktivno. Najprej ga aktivirajte.</p>}
    <div className="filter-bar">
     <label className="search-field">Poišči člana<span className="search-wrap"><Icon name="search"/><input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="E-pošta ali ime" autoComplete="off"/></span></label>
     <label>Vloga<select value={role} onChange={e => setRole(e.target.value)}><option value="vse">Vse vloge</option><option value="mojster">Mojster</option><option value="delavec">Delavec</option></select></label>
     <label>Stanje<select value={state} onChange={e => setState(e.target.value)}><option value="aktivne">Aktivne</option><option value="odvzete">Odvzete</option><option value="vse">Vse</option></select></label>
     <p className="result-count">{plural(members.length, ['član', 'člana', 'člani', 'članov'])}</p>
    </div>
    <div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">{`Člani podjetja ${company.naziv}`}</caption><thead><tr><th>Član</th><th>Vloga</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
     {members.map(r => <tr key={r.id} className={r.aktivna ? '' : 'muted'}><td><strong>{fullName(r)}</strong>{fullName(r) !== r.e_posta && <span className="cell-detail">{r.e_posta}</span>}</td>
      <td><span className="status-badge pending">{roleNames[r.vloga]}</span>{r.je_lastnik && <> <span className="status-badge confirmed">Lastnik</span></>}</td>
      <td data-label="Stanje:"><span className={`status-badge ${r.aktivna ? 'confirmed' : 'inactive'}`}>{r.aktivna ? 'Aktivna' : 'Odvzeta'}</span></td>
      <td className="num"><RoleAction role={r} busy={busy} protectedNote={r.je_lastnik && r.vloga === 'mojster' ? 'Lastnik ne more izgubiti vloge mojster. Najprej zamenjajte lastnika.' : undefined} onChange={(active, message) => onChange(r.id, active, message)}/></td></tr>)}
     {!members.length && <tr><td colSpan={4}><p>Ni članov, ki ustrezajo filtrom.</p><button type="button" className="secondary small" onClick={() => { setSearch(''); setRole('vse'); setState('vse'); }}>Počisti filtre</button></td></tr>}</tbody></table></div>
   </>}
  </div>
  {adding && company && <RoleDrawer title="Dodaj člana" busy={busy} error={error} onClose={() => { setAdding(false); onClearError(); }} onSubmit={async (vloga, data) => { if (await onAssign(String(data.get('uporabnik_id')), company.id, vloga)) setAdding(false); }}
   pick={vloga => <><label>Uporabnik<select name="uporabnik_id" required defaultValue=""><option value="" disabled>Izberite uporabnika</option>{options(vloga).map(u => <option key={u.id} value={u.id} disabled={admins.has(u.id)}>{`${fullName(u)} · ${u.e_posta}`}</option>)}</select></label>{options(vloga).some(u => admins.has(u.id)) && <p className="owner-note">Skrbnik si ne more sam dodeliti vloge v podjetju.</p>}</>}/>}
 </div>;
}
