import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { dateTime } from '../../../utils/format';
import { createProject, getProjects, requestSurvey, updateProject } from '../api';
import { phases, type Project } from '../types';
import ProjectForm from './ProjectForm';

export default function ProjectsWorkspace({ client, companyId }: { client: SupabaseClient; companyId: string }) {
 const [projects, setProjects] = useState<Project[]>([]);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [editing, setEditing] = useState<Project | null>(null);
 const sequence = useRef(0);
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try { const next = await getProjects(client, companyId); if (request === sequence.current) setProjects(next); }
  finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId]);
 useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Projektov ni mogoče naložiti.')); return () => { sequence.current++; }; }, [load]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setNotice(message); setEditing(null); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 const alert = error && <p role="alert" className="alert">{error}</p>;
 return <section className="supplier-view" aria-busy={loading}>
  <div className="page-title"><div><h1>Projekti</h1><p>Projekti podjetja po fazah, od pregleda do zaključka. {projects.length} skupaj.</p></div></div>
  {!editing && alert}
  {notice && <p role="status" className="notice"><Icon name="check"/>{notice}</p>}
  {!editing && <section className="panel"><h2>Nov projekt</h2><p>Stranka mora biti registrirana z navedenim e-poštnim naslovom.</p>
   <ProjectForm busy={busy || loading} onSave={async (data, reset) => { if (await mutate(() => createProject(client, companyId, data), 'Projekt je ustvarjen.')) reset(); }}/></section>}
  {loading ? <div className="loading-state" role="status">Nalagam projekte …</div> : !projects.length ? <div className="full-empty"><Icon name="list"/><h2>Še ni projektov</h2><p>Ustvarite prvi projekt za registrirano stranko.</p></div> : phases.map(([id, label]) => {
   const rows = projects.filter(project => project.faza === id);
   return rows.length > 0 && <section key={id} className="phase-section"><h2>{label}</h2>
    <div className="table-wrap"><table className="data-table phase-table"><caption className="sr-only">Projekti v fazi {label}</caption><thead><tr><th>Projekt</th><th>Stranka</th><th className="num">Termin</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
     {rows.map(project => <tr key={project.id}><td><strong>{project.naziv}</strong><span className="cell-detail">{project.lokacija_izvedbe}</span></td>
      <td>{project.stranka_ime} {project.stranka_priimek}<span className="cell-detail">{project.stranka_e_posta}</span></td>
      <td className="num" data-label="Termin">{project.termin_od ? `${dateTime(project.termin_od)} – ${dateTime(project.termin_do)}` : '—'}</td>
      <td>{project.faza === 'pregled' && <IconButton icon="calendar" label={`Zahtevaj ogled ${project.naziv}`} tip="Zahtevaj ogled" disabled={busy} onClick={() => void mutate(() => requestSurvey(client, companyId, project.id), 'Ogled je zahtevan.')}/>}<IconButton icon="pen" label={`Uredi ${project.naziv}`} tip="Uredi" disabled={busy} onClick={() => { setError(''); setNotice(''); setEditing(project); }}/></td></tr>)}
    </tbody></table></div></section>;
  })}
  {editing && <Drawer title="Uredi projekt" onClose={() => { if (!busy) setEditing(null); }}>
   {alert}
   <ProjectForm item={editing} busy={busy} onSave={async data => { await mutate(() => updateProject(client, companyId, editing.id, { naziv: data.naziv, opis: data.opis, lokacija_izvedbe: data.lokacija_izvedbe }), 'Projekt je shranjen.'); }}/>
  </Drawer>}
 </section>;
}
