import { useEffect, useState, type ReactNode } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { dateTime } from '../../../utils/format';
import useDetailFocus from '../../../utils/useDetailFocus';
import { getOwnProjects } from '../api';
import { phases, type OwnProject } from '../types';

export default function MyProjects({ client, renderQuote, renderInvoice }: { client: SupabaseClient; renderQuote?: (project: OwnProject) => ReactNode; renderInvoice?: (project: OwnProject) => ReactNode }) {
 const [projects, setProjects] = useState<OwnProject[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState('');
 const [detail, setDetail] = useState<{ project: OwnProject; kind: 'quote' | 'invoice' } | null>(null);
 const { heading, root, remember } = useDetailFocus(!!detail);
 useEffect(() => {
  let current = true;
  getOwnProjects(client).then(next => { if (current) setProjects(next); }).catch(e => { if (current) setError(e instanceof Error ? e.message : 'Projektov ni mogoče naložiti.'); }).finally(() => { if (current) setLoading(false); });
  return () => { current = false; };
 }, [client]);
 if (detail) { const shown = detail.project; return <section className="supplier-view" ref={root}><div className="page-title"><div><h1 tabIndex={-1} ref={heading}>{shown.naziv}</h1><p>{shown.lokacija_izvedbe}</p><p className="muted">Podjetje: {shown.podjetje_naziv} · Faza: {phases.find(([id]) => id === shown.faza)?.[1] ?? shown.faza}{shown.termin_od ? ` · Termin: ${dateTime(shown.termin_od)} – ${dateTime(shown.termin_do)}` : ''}</p></div><div className="title-actions"><button type="button" className="secondary" onClick={() => setDetail(null)}><Icon name="arrow"/>Nazaj na projekte</button></div></div>{detail.kind === 'quote' ? renderQuote?.(shown) : renderInvoice?.(shown)}</section>; }
 return <section className="supplier-view" aria-busy={loading} ref={root}>
  <div className="page-title"><div><h1 tabIndex={-1} ref={heading}>Moji projekti</h1><p>Projekti, ki so jih zanje ustvarila podjetja. Prikaz je samo za branje.</p></div></div>
  {error && <p role="alert" className="alert">{error}</p>}
  {loading ? <div className="loading-state" role="status">Nalagam projekte …</div> : !projects.length && !error ? <div className="full-empty"><Icon name="list"/><h2>Še nimate projektov</h2><p>Projekt se prikaže, ko ga za vas ustvari mojster.</p></div> : !!projects.length && <div className="table-wrap"><table className="data-table"><caption className="sr-only">Moji projekti</caption><thead><tr><th>Projekt</th><th>Faza</th><th>Podjetje</th><th className="num">Termin</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
   {projects.map(project => <tr key={project.id}><td><strong>{project.naziv}</strong><span className="cell-detail">{project.lokacija_izvedbe}</span></td>
    <td><span className="status-badge confirmed">{phases.find(([id]) => id === project.faza)?.[1] ?? project.faza}</span></td>
    <td data-label="Podjetje">{project.podjetje_naziv}</td>
    <td className="num" data-label="Termin">{project.termin_od ? `${dateTime(project.termin_od)} – ${dateTime(project.termin_do)}` : '—'}</td>
    <td>{renderInvoice && ['obracun', 'zakljucen'].includes(project.faza) && <IconButton icon="list" label={`Račun ${project.naziv}`} tip="Račun" onClick={() => { remember(`Račun ${project.naziv}`); setDetail({ project, kind: 'invoice' }); }}/>}{renderQuote && ['ponudba', 'termin', 'izvedba', 'obracun', 'zakljucen'].includes(project.faza) && <IconButton icon="calculator" label={`Ponudba ${project.naziv}`} tip="Ponudba" onClick={() => { remember(`Ponudba ${project.naziv}`); setDetail({ project, kind: 'quote' }); }}/>}</td></tr>)}
  </tbody></table></div>}
 </section>;
}
