import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { dateTime } from '../../../utils/format';
import useDetailFocus from '../../../utils/useDetailFocus';
import { createProject, getProjects, requestSurvey, updateProject } from '../api';
import { phases, type Project } from '../types';
import ProjectForm from './ProjectForm';

type Kind = 'items' | 'quote' | 'progress' | 'invoice';
const later = (project: Project) => ['termin', 'izvedba', 'obracun', 'zakljucen'].includes(project.faza);

export default function ProjectsWorkspace({ client, companyId, renderItems, renderQuote, renderProgress, renderInvoice }: { client: SupabaseClient; companyId: string; renderItems?: (project: Project) => ReactNode; renderQuote?: (project: Project, openItems: () => void) => ReactNode; renderProgress?: (project: Project, refresh: () => void) => ReactNode; renderInvoice?: (project: Project) => ReactNode }) {
 const [projects, setProjects] = useState<Project[]>([]);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [editing, setEditing] = useState<Project | null>(null);
 const [detail, setDetail] = useState<{ id: string; kind: Kind } | null>(null);
 const sequence = useRef(0);
 const { heading, root, remember } = useDetailFocus(!!detail);
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
 const shownProject = detail && projects.find(project => project.id === detail.id);
 if (detail && shownProject) {
  const body = detail.kind === 'items' ? renderItems?.(shownProject) : detail.kind === 'quote' ? renderQuote?.(shownProject, () => setDetail({ id: shownProject.id, kind: 'items' })) : detail.kind === 'progress' ? renderProgress?.(shownProject, () => { void load().catch(() => undefined); }) : renderInvoice?.(shownProject);
  const tabs: [Kind, string, Parameters<typeof Icon>[0]['name'], boolean][] = [['items', 'Postavke', 'ruler', !!renderItems], ['quote', 'Ponudba', 'calculator', !!renderQuote], ['progress', 'Potek', 'calendar', !!renderProgress && later(shownProject)], ['invoice', 'Račun', 'list', !!renderInvoice && later(shownProject)]];
  return <section className="supplier-view" ref={root}><div className="page-title"><div><h1 tabIndex={-1} ref={heading}>{shownProject.naziv}</h1><p>{shownProject.lokacija_izvedbe}</p><p className="muted">Stranka: {shownProject.stranka_ime} {shownProject.stranka_priimek} · Faza: {phases.find(([id]) => id === shownProject.faza)?.[1] ?? shownProject.faza}{shownProject.termin_od ? ` · Termin: ${dateTime(shownProject.termin_od)} – ${dateTime(shownProject.termin_do)}` : ''}</p></div>
   <div className="title-actions">{tabs.filter(([kind, , , show]) => show && kind !== detail.kind).map(([kind, label, icon]) => <button key={kind} type="button" className="secondary" aria-label={`${label} ${shownProject.naziv}`} onClick={() => setDetail({ id: shownProject.id, kind })}><Icon name={icon}/>{label}</button>)}
    <button type="button" className="secondary" onClick={() => { setDetail(null); void load().catch(() => undefined); }}><Icon name="arrow"/>Nazaj na projekte</button></div></div>{body}</section>;
 }
 const alert = error && <p role="alert" className="alert">{error}</p>;
 return <section className="supplier-view" aria-busy={loading} ref={root}>
  <div className="page-title"><div><h1 tabIndex={-1} ref={heading}>Projekti</h1><p>Projekti podjetja po fazah, od pregleda do zaključka. {projects.length} skupaj.</p></div></div>
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
      <td>{renderProgress && later(project) && <IconButton icon="calendar" label={`Izvedba ${project.naziv}`} tip="Izvedba" disabled={busy} onClick={() => { remember(`Izvedba ${project.naziv}`); setDetail({ id: project.id, kind: 'progress' }); }}/>}{renderInvoice && later(project) && <IconButton icon="list" label={`Račun ${project.naziv}`} tip="Račun" disabled={busy} onClick={() => { remember(`Račun ${project.naziv}`); setDetail({ id: project.id, kind: 'invoice' }); }}/>}{renderItems && <IconButton icon="ruler" label={`Postavke ${project.naziv}`} tip="Postavke" disabled={busy} onClick={() => { remember(`Postavke ${project.naziv}`); setDetail({ id: project.id, kind: 'items' }); }}/>}{renderQuote && <IconButton icon="calculator" label={`Ponudba ${project.naziv}`} tip="Ponudba" disabled={busy} onClick={() => { remember(`Ponudba ${project.naziv}`); setDetail({ id: project.id, kind: 'quote' }); }}/>}{project.faza === 'pregled' && <IconButton icon="calendar" label={`Zahtevaj ogled ${project.naziv}`} tip="Zahtevaj ogled" disabled={busy} onClick={() => void mutate(() => requestSurvey(client, companyId, project.id), 'Ogled je zahtevan.')}/>}<IconButton icon="pen" label={`Uredi ${project.naziv}`} tip="Uredi" disabled={busy} onClick={() => { setError(''); setNotice(''); setEditing(project); }}/></td></tr>)}
    </tbody></table></div></section>;
  })}
  {editing && <Drawer title="Uredi projekt" onClose={() => { if (!busy) setEditing(null); }}>
   {alert}
   <ProjectForm item={editing} busy={busy} onSave={async data => { await mutate(() => updateProject(client, companyId, editing.id, { naziv: data.naziv, opis: data.opis, lokacija_izvedbe: data.lokacija_izvedbe }), 'Projekt je shranjen.'); }}/>
  </Drawer>}
 </section>;
}
